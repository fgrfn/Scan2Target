"""Scan execution — single page, ADF batch, preview."""
from __future__ import annotations

import asyncio
import base64
import logging
import subprocess
from pathlib import Path

from app.scanning.discovery import SCAN_PROFILES

logger = logging.getLogger(__name__)

_ADF_EMPTY = ("out of documents", "no documents", "document feeder empty",
              "feeder empty", "flatbed only")


def _timeout() -> int:
    from app.app_settings.service import get_setting
    return get_setting("command_timeout", 15)


def _temp_dir() -> Path:
    from app.config import get_settings
    p = Path(get_settings().temp_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_profile(profile_id: str) -> dict | None:
    return next((p for p in SCAN_PROFILES if p["id"] == profile_id), None)


def _scan_page(uri: str, profile: dict, out_path: Path) -> None:
    cmd = [
        "scanimage",
        f"--device-name={uri}",
        f"--resolution={profile['dpi']}",
        f"--mode={profile['color_mode']}",
        "--format=tiff",
        f"--output-file={out_path}",
    ]
    if profile.get("source") == "ADF":
        cmd.append("--source=ADF")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        stderr = r.stderr.strip() or r.stdout.strip()
        if stderr:
            logger.error("scanimage stderr: %s", stderr)
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)


def _convert_to_pdf(tiff_paths: list[Path], out_pdf: Path) -> None:
    args = ["convert", "-compress", "jpeg", "-quality", "85"]
    args += [str(p) for p in tiff_paths]
    args.append(str(out_pdf))
    subprocess.run(args, capture_output=True, text=True, timeout=60, check=True)


def _convert_to_jpeg(tiff_path: Path, out_jpeg: Path) -> None:
    subprocess.run(["convert", str(tiff_path), str(out_jpeg)],
                   capture_output=True, text=True, timeout=30, check=True)


def _make_thumbnail(tiff_path: Path, thumb_path: Path) -> None:
    subprocess.run(["convert", str(tiff_path), "-thumbnail", "400x400>", str(thumb_path)],
                   capture_output=True, text=True, timeout=15)


async def scan_and_deliver(job_id: str, uri: str, profile_id: str, target_id: str,
                            filename_prefix: str, webhook_url: str | None) -> None:
    """Full scan pipeline — runs in a background worker task."""
    from app.jobs import service as jobs
    from app.targets.service import deliver
    from app.ws.manager import get_ws_manager

    ws = get_ws_manager()
    profile = get_profile(profile_id)
    if not profile:
        jobs.update_status(job_id, "failed", f"Unknown profile: {profile_id}")
        return

    tmp = _temp_dir()
    tiff_paths: list[Path] = []
    thumb_path = tmp / f"{filename_prefix}_{job_id}_thumb.jpg"

    # Update to running
    job = jobs.update_status(job_id, "running")
    if job:
        await ws.broadcast_job(job)

    try:
        if profile["source"] == "ADF":
            page = 0
            while True:
                page += 1
                tiff = tmp / f"{filename_prefix}_{job_id}_p{page:03d}.tiff"
                try:
                    await asyncio.to_thread(_scan_page, uri, profile, tiff)
                    tiff_paths.append(tiff)
                    if page == 1:
                        await asyncio.to_thread(_make_thumbnail, tiff, thumb_path)
                        job = jobs.update_status(job_id, "running", file_path=str(thumb_path))
                        if job:
                            await ws.broadcast_job(job)
                except subprocess.CalledProcessError as e:
                    err = (e.stderr or "").lower()
                    if any(m in err for m in _ADF_EMPTY):
                        break
                    raise
        else:
            tiff = tmp / f"{filename_prefix}_{job_id}.tiff"
            await asyncio.to_thread(_scan_page, uri, profile, tiff)
            tiff_paths.append(tiff)
            await asyncio.to_thread(_make_thumbnail, tiff, thumb_path)
            job = jobs.update_status(job_id, "running", file_path=str(thumb_path))
            if job:
                await ws.broadcast_job(job)

        if not tiff_paths:
            raise RuntimeError("No pages scanned")

        # Convert
        if profile["format"] == "pdf":
            out = tmp / f"{filename_prefix}_{job_id}.pdf"
            await asyncio.to_thread(_convert_to_pdf, tiff_paths, out)
        else:
            out = tmp / f"{filename_prefix}_{job_id}.{profile['format']}"
            await asyncio.to_thread(_convert_to_jpeg, tiff_paths[0], out)

        # Clean up TIFFs
        for t in tiff_paths:
            t.unlink(missing_ok=True)

        # Deliver
        filename = f"{filename_prefix}_{job_id}.{profile['format']}"
        await asyncio.to_thread(deliver, target_id, out, filename)
        out.unlink(missing_ok=True)

        job = jobs.update_status(job_id, "completed")
        if job:
            await ws.broadcast_job(job)

    except Exception as exc:
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            stderr = exc.stderr.strip()
            fail_msg = f"Scan failed: {stderr}"
            logger.error("Job %s failed: %s", job_id, fail_msg)
        else:
            fail_msg = str(exc)
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        for t in tiff_paths:
            t.unlink(missing_ok=True)
        job = jobs.update_status(job_id, "failed", fail_msg)
        if job:
            await ws.broadcast_job(job)

    finally:
        if webhook_url:
            await asyncio.to_thread(
                _notify_webhook, webhook_url, job_id,
                job.get("status", "unknown") if job else "unknown"
            )


def _notify_webhook(url: str, job_id: str, status: str) -> None:
    import requests
    try:
        requests.post(url, json={"job_id": job_id, "status": status}, timeout=10)
    except Exception as exc:
        logger.warning("Webhook notification failed: %s", exc)


async def scan_preview(uri: str, profile_id: str) -> str:
    """Quick low-res preview scan — returns base64-encoded JPEG."""
    profile = get_profile(profile_id) or {"dpi": 75, "color_mode": "Color", "source": "Flatbed"}
    low_res = dict(profile, dpi=75, format="tiff", source="Flatbed")
    tmp = _temp_dir()
    tiff = tmp / f"preview_{uri.replace('/', '_')}.tiff"
    try:
        await asyncio.to_thread(_scan_page, uri, low_res, tiff)
        jpeg = tiff.with_suffix(".jpg")
        await asyncio.to_thread(_convert_to_jpeg, tiff, jpeg)
        data = jpeg.read_bytes()
        jpeg.unlink(missing_ok=True)
        return base64.b64encode(data).decode()
    finally:
        tiff.unlink(missing_ok=True)


async def scan_and_save_page(uri: str, profile_id: str) -> tuple[str, Path]:
    """Scan a single page at full profile resolution, persist the TIFF, return (preview_b64, tiff_path).

    Used by batch mode: the caller collects tiff_paths and later calls combine_batch().
    """
    import uuid
    profile = get_profile(profile_id) or {"dpi": 200, "color_mode": "Gray", "format": "pdf", "source": "Flatbed"}
    tmp = _temp_dir()
    tiff = tmp / f"batch_{uuid.uuid4().hex[:8]}.tiff"
    await asyncio.to_thread(_scan_page, uri, profile, tiff)
    # Create a low-res JPEG preview without deleting the TIFF
    thumb = tiff.with_suffix(".jpg")
    await asyncio.to_thread(_make_thumbnail, tiff, thumb)
    try:
        data = thumb.read_bytes()
    finally:
        thumb.unlink(missing_ok=True)
    return base64.b64encode(data).decode(), tiff


async def combine_batch(job_id: str, target_id: str, filename_prefix: str,
                         page_paths: list[str]) -> None:
    """Combine pre-scanned preview pages into a PDF and deliver."""
    from app.jobs import service as jobs
    from app.targets.service import deliver
    from app.ws.manager import get_ws_manager

    ws = get_ws_manager()
    job = jobs.update_status(job_id, "running")
    if job:
        await ws.broadcast_job(job)
    tmp = _temp_dir()
    try:
        paths = [Path(p) for p in page_paths if Path(p).exists()]
        if not paths:
            raise RuntimeError("No valid page paths")
        out = tmp / f"{filename_prefix}_{job_id}.pdf"
        await asyncio.to_thread(_convert_to_pdf, paths, out)
        filename = f"{filename_prefix}_{job_id}.pdf"
        await asyncio.to_thread(deliver, target_id, out, filename)
        out.unlink(missing_ok=True)
        job = jobs.update_status(job_id, "completed")
        if job:
            await ws.broadcast_job(job)
    except Exception as exc:
        job = jobs.update_status(job_id, "failed", str(exc))
        if job:
            await ws.broadcast_job(job)
