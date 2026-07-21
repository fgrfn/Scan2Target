"""Scanning orchestration and cancellable SANE process execution."""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from io import BytesIO
from typing import List

import requests
from PIL import Image

from core.config.settings import get_settings
from core.delivery.retry import get_delivery_retry_service
from core.jobs.manager import JobManager
from core.jobs.models import JobRecord, JobStatus
from core.scanning.process_registry import ScanCancelledError, get_process_registry, run_cancellable
from core.scanning.profiles import get_profile_repository
from core.validation import sanitize_filename_prefix, validate_webhook_url
from core.worker import get_worker

logger = logging.getLogger(__name__)


class ScannerManager:
    """Discover scanners and orchestrate scan, processing and delivery jobs."""

    _locks_guard = threading.Lock()
    _device_locks: dict[str, threading.Lock] = {}

    @classmethod
    def _device_lock(cls, device_id: str) -> threading.Lock:
        with cls._locks_guard:
            return cls._device_locks.setdefault(device_id, threading.Lock())

    def list_devices(self) -> List[dict]:
        devices: list[dict] = []
        groups: dict[str, list[dict]] = {}
        try:
            result = subprocess.run(
                ["airscan-discover"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning("airscan-discover failed: %s", result.stderr.strip())
                return []
            in_devices = False
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if line == "[devices]":
                    in_devices = True
                    continue
                if not in_devices or not line or line.startswith("[") or "=" not in line:
                    continue
                name_part, url_part = (part.strip() for part in line.split("=", 1))
                parts = [part.strip() for part in url_part.split(",")]
                url = parts[0]
                protocol = parts[1] if len(parts) > 1 else "Unknown"
                match = re.match(r"(.+?)\s*\[([^\]]+)\]", name_part)
                device_name = match.group(1).strip() if match else name_part
                serial = match.group(2).strip() if match else None
                if protocol == "eSCL":
                    is_usb = "127.0.0.1" in url or "::1" in url or "USB" in name_part
                    device_type = "eSCL (USB)" if is_usb else "eSCL (Network)"
                    priority = 2 if is_usb else 1
                elif protocol == "WSD":
                    device_type, priority = "WSD (Network)", 3
                else:
                    device_type, priority = protocol, 99
                device_id = f"airscan:escl:{device_name.replace(' ', '_')}:{url}"
                groups.setdefault(device_name, []).append(
                    {
                        "id": device_id,
                        "name": f"{device_name} [{serial}]" if serial else device_name,
                        "type": device_type,
                        "priority": priority,
                        "supported": True,
                    }
                )
            for base_name, group in groups.items():
                group.sort(key=lambda item: item["priority"])
                network = next((item for item in group if item["priority"] == 1), None)
                usb = next((item for item in group if item["priority"] == 2), None)
                if network and usb:
                    network["name"] = f"{base_name} (Network - Recommended)"
                    usb["name"] = f"{base_name} (USB)"
                    devices.extend((network, usb))
                else:
                    devices.append(group[0])
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("Scanner discovery unavailable: %s", exc)
        except Exception as exc:
            logger.error("Scanner discovery failed: %s", exc, exc_info=True)
        return devices

    def list_profiles(self) -> List[dict]:
        return get_profile_repository().list()

    def resolve_profile(self, profile_id: str | None) -> dict:
        return get_profile_repository().resolve(profile_id)

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def capture_pages(
        self,
        device_id: str,
        profile_id: str,
        source: str | None = None,
        batch: bool = False,
        cancellation_id: str | None = None,
    ) -> list[str]:
        """Capture browser-editable JPEG pages without creating a delivery job."""
        device_lock = self._device_lock(device_id)
        if not device_lock.acquire(blocking=False):
            raise RuntimeError("Scanner is busy")

        work_dir = Path(tempfile.mkdtemp(prefix="scan2target-capture-"))
        try:
            profile = self.resolve_profile(profile_id)
            scan_source = source or profile.get("source", "Flatbed")
            common = [
                "scanimage",
                "--device-name",
                device_id,
                "--resolution",
                str(profile.get("dpi", 200)),
                "--mode",
                str(profile.get("color_mode", "Gray")),
                "--format",
                "tiff",
            ]
            if scan_source:
                common.extend(["--source", scan_source])

            if batch:
                pattern = work_dir / "page%03d.tiff"
                command = [*common, f"--batch={pattern}"]
                result = (
                    run_cancellable(
                        cancellation_id,
                        command,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if cancellation_id
                    else subprocess.run(command, capture_output=True, text=True, timeout=300)
                )
                files = [path for path in sorted(work_dir.glob("page*.tiff")) if path.stat().st_size]
            else:
                page = work_dir / "page001.tiff"
                with page.open("wb") as output:
                    result = (
                        run_cancellable(
                            cancellation_id,
                            common,
                            stdout=output,
                            stderr=subprocess.PIPE,
                            timeout=120,
                        )
                        if cancellation_id
                        else subprocess.run(
                            common, stdout=output, stderr=subprocess.PIPE, timeout=120
                        )
                    )
                files = [page] if page.exists() and page.stat().st_size else []

            if result.returncode != 0 and not (batch and files):
                error = result.stderr or result.stdout or b"Scan failed"
                if isinstance(error, bytes):
                    error = error.decode("utf-8", errors="replace")
                raise RuntimeError(str(error).strip())
            if not files:
                raise RuntimeError("No pages were scanned")

            pages: list[str] = []
            for path in files[:100]:
                with Image.open(path) as image:
                    output = BytesIO()
                    image.convert("RGB").save(
                        output,
                        format="JPEG",
                        quality=int(profile.get("quality", 85)),
                    )
                encoded = base64.b64encode(output.getvalue()).decode("ascii")
                pages.append(f"data:image/jpeg;base64,{encoded}")
            return pages
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            device_lock.release()
            if cancellation_id:
                get_process_registry().finish(cancellation_id)

    def get_job(self, job_id: str) -> JobRecord | None:
        return JobManager().get_job(job_id)

    def start_scan(
        self,
        device_id: str,
        profile_id: str,
        target_id: str,
        filename_prefix: str | None,
        source: str | None = None,
        webhook_url: str | None = None,
    ) -> str:
        settings = get_settings()
        job_id = str(uuid.uuid4())
        safe_prefix = sanitize_filename_prefix(filename_prefix, "scan")
        safe_webhook = validate_webhook_url(webhook_url) if webhook_url else None
        JobManager().create_job(
            job_id=job_id,
            job_type="scan",
            device_id=device_id,
            target_id=target_id,
            status=JobStatus.queued,
            max_retries=settings.delivery_max_retries,
            metadata={
                "profile_id": profile_id,
                "filename_prefix": safe_prefix,
                "webhook_url": safe_webhook,
            },
        )

        async def scan_task():
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._execute_scan,
                job_id,
                device_id,
                profile_id,
                target_id,
                safe_prefix,
                source,
                safe_webhook,
            )

        get_worker().submit_task(job_id, scan_task)
        return job_id

    def _execute_scan(
        self,
        job_id: str,
        device_id: str,
        profile_id: str,
        target_id: str,
        filename_prefix: str,
        source_override: str | None = None,
        webhook_url: str | None = None,
    ) -> None:
        jobs = JobManager()
        registry = get_process_registry()
        scanned_files: list[Path] = []
        final_file: Path | None = None
        device_lock = self._device_lock(device_id)
        if not device_lock.acquire(blocking=False):
            jobs.transition(job_id, JobStatus.failed, message="Scanner is already processing another job")
            raise RuntimeError("Scanner is busy")

        try:
            registry.ensure_not_cancelled(job_id)
            jobs.transition(job_id, JobStatus.scanning, message="Scanning document")
            profile = self.resolve_profile(profile_id)
            temp_dir = Path(tempfile.gettempdir()) / "scan2target" / "scans"
            temp_dir.mkdir(parents=True, exist_ok=True)
            persistent_dir = get_settings().data_dir / "scans"
            persistent_dir.mkdir(parents=True, exist_ok=True)
            source = source_override or profile.get("source", "Flatbed")
            if bool(profile.get("batch_scan")) and source.lower().startswith("adf"):
                scanned_files = self._scan_adf_batch(
                    job_id, device_id, profile, source, temp_dir, filename_prefix
                )
            else:
                scanned_files = [
                    self._scan_single_page(
                        job_id, device_id, profile, source, temp_dir, filename_prefix
                    )
                ]

            registry.ensure_not_cancelled(job_id)
            jobs.transition(job_id, JobStatus.processing, message="Processing scan")
            final_file = self._convert_output(
                job_id, scanned_files, profile, persistent_dir, filename_prefix
            )
            thumbnail = self._create_thumbnail(job_id, final_file, temp_dir, filename_prefix)
            job = jobs.get_job(job_id)
            if job:
                job.file_path = str(final_file)
                job.thumbnail_path = str(thumbnail) if thumbnail else None
                job.metadata.update(
                    {"pages": len(scanned_files), "format": profile.get("format"), "profile_id": profile_id}
                )
                jobs.update_job(job)

            registry.ensure_not_cancelled(job_id)
            delivered = get_delivery_retry_service().deliver_now(job_id)
            final_job = jobs.get_job(job_id)
            if webhook_url and final_job:
                self._send_webhook_notification(
                    webhook_url,
                    job_id,
                    final_job.status.value,
                    {
                        "pages": len(scanned_files),
                        "format": profile.get("format"),
                        "retry_count": final_job.retry_count,
                    },
                )
            if not delivered and final_job and final_job.status == JobStatus.delivery_failed:
                logger.warning("Job %s scanned successfully but delivery failed permanently", job_id)
        except ScanCancelledError:
            jobs.transition(job_id, JobStatus.cancelled, message="Scan cancelled by user")
        except Exception as exc:
            logger.error("Scan job %s failed: %s", job_id, exc, exc_info=True)
            job = jobs.get_job(job_id)
            if job and job.status not in {JobStatus.retry_scheduled, JobStatus.delivery_failed, JobStatus.cancelled}:
                jobs.transition(job_id, JobStatus.failed, message=str(exc), last_error=str(exc))
            if final_file and final_file.exists():
                final_file.unlink(missing_ok=True)
            if webhook_url:
                self._send_webhook_notification(webhook_url, job_id, "failed", {"error": str(exc)})
            raise
        finally:
            for path in scanned_files:
                path.unlink(missing_ok=True)
            registry.finish(job_id)
            device_lock.release()

    def _scan_adf_batch(
        self,
        job_id: str,
        device_id: str,
        profile: dict,
        source: str,
        output_dir: Path,
        prefix: str,
    ) -> list[Path]:
        pattern = output_dir / f"{prefix}_{job_id}_page%03d.tiff"
        cmd = [
            "scanimage", "--device-name", device_id,
            "--resolution", str(profile["dpi"]),
            "--mode", profile["color_mode"],
            "--format", "tiff", "--source", source,
            f"--batch={pattern}",
        ]
        result = run_cancellable(job_id, cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "ADF scan failed").strip())
        pages = [page for page in sorted(output_dir.glob(f"{prefix}_{job_id}_page*.tiff")) if page.stat().st_size]
        if not pages:
            raise RuntimeError("No pages were scanned")
        return pages[:100]

    def _scan_single_page(
        self,
        job_id: str,
        device_id: str,
        profile: dict,
        source: str | None,
        output_dir: Path,
        prefix: str,
    ) -> Path:
        output = output_dir / f"{prefix}_{job_id}.tiff"
        cmd = [
            "scanimage", "--device-name", device_id,
            "--resolution", str(profile["dpi"]),
            "--mode", profile["color_mode"],
            "--format", "tiff",
        ]
        if source and source != "Flatbed":
            cmd.extend(["--source", source])
        with output.open("wb") as stream:
            result = run_cancellable(
                job_id, cmd, stdout=stream, stderr=subprocess.PIPE, timeout=120
            )
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise RuntimeError(f"scanimage failed: {error}")
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("Scanner returned an empty file")
        return output

    def _convert_output(
        self,
        job_id: str,
        scanned_files: list[Path],
        profile: dict,
        output_dir: Path,
        prefix: str,
    ) -> Path:
        output_format = str(profile.get("format", "pdf")).lower()
        suffix = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "tiff": "tiff"}.get(output_format, "pdf")
        output = output_dir / f"{prefix}_{job_id}.{suffix}"
        if output_format in {"tiff", "tif"} and len(scanned_files) == 1:
            shutil.copy2(scanned_files[0], output)
            return output
        cmd = ["convert", *map(str, scanned_files)]
        if suffix == "pdf":
            cmd.extend(["-compress", "JPEG", "-quality", str(profile.get("quality", 85))])
        elif suffix in {"jpg", "png"}:
            cmd.extend(["-quality", str(profile.get("quality", 85))])
        cmd.append(str(output))
        result = run_cancellable(job_id, cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0 or not output.exists():
            raise RuntimeError(f"Scan conversion failed: {result.stderr or result.stdout}")
        return output

    def _create_thumbnail(
        self, job_id: str, file: Path, output_dir: Path, prefix: str
    ) -> Path | None:
        thumbnail = output_dir / f"{prefix}_{job_id}_thumb.jpg"
        source = f"{file}[0]" if file.suffix.lower() == ".pdf" else str(file)
        result = run_cancellable(
            job_id,
            ["convert", source, "-thumbnail", "320x320>", "-quality", "75", str(thumbnail)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not thumbnail.exists():
            logger.warning("Thumbnail creation failed for job %s", job_id)
            return None
        return thumbnail

    @staticmethod
    def _send_webhook_notification(
        url: str, job_id: str, status: str, details: dict
    ) -> None:
        try:
            requests.post(
                url,
                json={"job_id": job_id, "status": status, "details": details},
                timeout=10,
                allow_redirects=False,
            ).raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Scan notification webhook failed: %s", exc)
