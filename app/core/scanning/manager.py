"""Scanning orchestration and cancellable SANE process execution."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests

from core.jobs.manager import JobManager
from core.jobs.models import JobRecord, JobStatus
from core.scanning.process_registry import (
    ScanCancelledError,
    get_process_registry,
    run_cancellable,
)
from core.scanning.profiles import get_profile_repository
from core.targets.manager import TargetManager
from core.validation import sanitize_filename_prefix, validate_webhook_url
from core.worker import get_worker

logger = logging.getLogger(__name__)


class ScannerManager:
    """Discover scanners and orchestrate scan, conversion and delivery jobs."""

    _locks_guard = threading.Lock()
    _device_locks: dict[str, threading.Lock] = {}

    @classmethod
    def _device_lock(cls, device_id: str) -> threading.Lock:
        with cls._locks_guard:
            return cls._device_locks.setdefault(device_id, threading.Lock())

    def list_devices(self) -> List[dict]:
        """Discover eSCL/AirScan devices and prefer network endpoints."""
        devices: list[dict] = []
        device_groups: dict[str, list[dict]] = {}
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

            in_devices_section = False
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if line == "[devices]":
                    in_devices_section = True
                    continue
                if not in_devices_section or not line or line.startswith("[") or "=" not in line:
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
                    device_type = "WSD (Network)"
                    priority = 3
                else:
                    device_type = protocol
                    priority = 99

                device_id = f"airscan:escl:{device_name.replace(' ', '_')}:{url}"
                device_groups.setdefault(device_name, []).append(
                    {
                        "id": device_id,
                        "name": f"{device_name} [{serial}]" if serial else device_name,
                        "type": device_type,
                        "priority": priority,
                        "supported": True,
                    }
                )

            for base_name, group in device_groups.items():
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

        logger.info("Scanner discovery completed: %s device(s)", len(devices))
        return devices

    def list_profiles(self) -> List[dict]:
        return get_profile_repository().list()

    def resolve_profile(self, profile_id: str | None) -> dict:
        return get_profile_repository().resolve(profile_id)

    def start_scan(
        self,
        device_id: str,
        profile_id: str,
        target_id: str,
        filename_prefix: str | None,
        source: str | None = None,
        webhook_url: str | None = None,
    ) -> str:
        """Create and submit a scan job."""
        job_id = str(uuid.uuid4())
        JobManager().create_job(
            job_id=job_id,
            job_type="scan",
            device_id=device_id,
            target_id=target_id,
            status=JobStatus.queued,
        )

        safe_prefix = sanitize_filename_prefix(filename_prefix, "scan")
        safe_webhook = validate_webhook_url(webhook_url) if webhook_url else None

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
        job_manager = JobManager()
        registry = get_process_registry()
        scanned_files: list[Path] = []
        final_file: Path | None = None
        thumbnail_file: Path | None = None
        device_lock = self._device_lock(device_id)

        if not device_lock.acquire(blocking=False):
            self._fail_job(job_manager, job_id, "Scanner is already processing another job")
            raise RuntimeError("Scanner is busy")

        try:
            registry.ensure_not_cancelled(job_id)
            job = job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.running
                job.message = None
                job_manager.update_job(job)

            profile = self.resolve_profile(profile_id)
            output_dir = Path(tempfile.gettempdir()) / "scan2target" / "scans"
            output_dir.mkdir(parents=True, exist_ok=True)
            source = source_override or profile.get("source", "Flatbed")
            batch_scan = bool(profile.get("batch_scan"))

            if batch_scan and source and source.lower().startswith("adf"):
                scanned_files = self._scan_adf_batch(
                    job_id, device_id, profile, source, output_dir, filename_prefix
                )
            else:
                scanned_files = [
                    self._scan_single_page(
                        job_id, device_id, profile, source, output_dir, filename_prefix
                    )
                ]

            registry.ensure_not_cancelled(job_id)
            final_file = self._convert_output(
                job_id, scanned_files, profile, output_dir, filename_prefix
            )
            thumbnail_file = self._create_thumbnail(
                job_id, final_file, output_dir, filename_prefix
            )

            job = job_manager.get_job(job_id)
            if job:
                job.file_path = str(final_file)
                job.thumbnail_path = str(thumbnail_file) if thumbnail_file else None
                job_manager.update_job(job)

            registry.ensure_not_cancelled(job_id)
            TargetManager().deliver(target_id, str(final_file), {"job_id": job_id})
            registry.ensure_not_cancelled(job_id)

            job = job_manager.get_job(job_id)
            if job and job.status != JobStatus.cancelled:
                job.status = JobStatus.completed
                job.message = None
                job_manager.update_job(job)

            if final_file.exists():
                final_file.unlink()
            if webhook_url:
                self._send_webhook_notification(
                    webhook_url,
                    job_id,
                    "completed",
                    {
                        "pages": len(scanned_files),
                        "format": profile.get("format"),
                        "profile": profile_id,
                    },
                )
        except ScanCancelledError:
            job = job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.cancelled
                job.message = "Scan cancelled by user"
                job_manager.update_job(job)
            logger.info("Scan job %s cancelled", job_id)
        except Exception as exc:
            logger.error("Scan job %s failed: %s", job_id, exc, exc_info=True)
            self._fail_job(job_manager, job_id, str(exc))
            if webhook_url:
                self._send_webhook_notification(
                    webhook_url, job_id, "failed", {"error": str(exc)}
                )
            raise
        finally:
            for path in scanned_files:
                if path != final_file:
                    path.unlink(missing_ok=True)
            registry.finish(job_id)
            device_lock.release()

    @staticmethod
    def _fail_job(job_manager: JobManager, job_id: str, message: str) -> None:
        job = job_manager.get_job(job_id)
        if job and job.status != JobStatus.cancelled:
            job.status = JobStatus.failed
            job.message = message
            job_manager.update_job(job)

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
            "scanimage",
            "--device-name",
            device_id,
            "--resolution",
            str(profile["dpi"]),
            "--mode",
            profile["color_mode"],
            "--format",
            "tiff",
            "--source",
            source,
            f"--batch={pattern}",
        ]
        result = run_cancellable(
            job_id, cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "ADF scan failed").strip())
        pages = sorted(output_dir.glob(f"{prefix}_{job_id}_page*.tiff"))
        pages = [page for page in pages if page.stat().st_size > 0]
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
        tiff_file = output_dir / f"{prefix}_{job_id}.tiff"
        cmd = [
            "scanimage",
            "--device-name",
            device_id,
            "--resolution",
            str(profile["dpi"]),
            "--mode",
            profile["color_mode"],
            "--format",
            "tiff",
        ]
        if source and source != "Flatbed":
            cmd.extend(["--source", source])
        with tiff_file.open("wb") as output:
            result = run_cancellable(
                job_id,
                cmd,
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=120,
            )
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise RuntimeError(f"scanimage failed: {error}")
        if not tiff_file.exists() or tiff_file.stat().st_size == 0:
            raise RuntimeError("Scanner returned an empty file")
        return tiff_file

    def _convert_output(
        self,
        job_id: str,
        scanned_files: list[Path],
        profile: dict,
        output_dir: Path,
        prefix: str,
    ) -> Path:
        output_format = str(profile.get("format", "pdf")).lower()
        if output_format == "pdf":
            output = output_dir / f"{prefix}_{job_id}.pdf"
            cmd = ["convert", *map(str, scanned_files), "-compress", "JPEG"]
            cmd.extend(["-quality", str(profile.get("quality", 85))])
            cmd.extend(["-density", str(profile.get("dpi", 200))])
            if profile.get("color_mode") == "Gray":
                cmd.extend(["-colorspace", "Gray"])
            cmd.append(str(output))
            result = run_cancellable(
                job_id, cmd, capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0 or not output.exists():
                raise RuntimeError(f"PDF conversion failed: {result.stderr or result.stdout}")
            return output

        if output_format in {"jpeg", "jpg"}:
            output = output_dir / f"{prefix}_{job_id}.jpg"
            result = run_cancellable(
                job_id,
                [
                    "convert",
                    str(scanned_files[0]),
                    "-quality",
                    str(profile.get("quality", 90)),
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0 or not output.exists():
                raise RuntimeError(f"JPEG conversion failed: {result.stderr or result.stdout}")
            return output

        return scanned_files[0]

    def _create_thumbnail(
        self, job_id: str, final_file: Path, output_dir: Path, prefix: str
    ) -> Path | None:
        thumbnail = output_dir / f"{prefix}_{job_id}_thumb.jpg"
        result = run_cancellable(
            job_id,
            [
                "convert",
                f"{final_file}[0]",
                "-thumbnail",
                "400x400>",
                "-quality",
                "80",
                str(thumbnail),
            ],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0 and thumbnail.exists():
            return thumbnail
        logger.warning("Thumbnail generation failed for %s", job_id)
        return None

    def _send_webhook_notification(
        self, webhook_url: str, job_id: str, status: str, metadata: dict
    ) -> None:
        """Send a non-redirecting, validated status webhook."""
        try:
            safe_url = validate_webhook_url(webhook_url)
            response = requests.post(
                safe_url,
                json={
                    "job_id": job_id,
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata,
                },
                timeout=10,
                allow_redirects=False,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Webhook notification failed: %s", exc)

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def get_job(self, job_id: str) -> JobRecord | None:
        return JobManager().get_job(job_id)
