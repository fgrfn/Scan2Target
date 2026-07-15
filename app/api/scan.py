"""Scan-related API routes."""
from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator, model_validator

from core.devices.repository import DeviceRepository
from core.jobs.manager import JobManager
from core.jobs.models import JobRecord, JobStatus
from core.scanning.manager import ScannerManager
from core.targets.manager import TargetManager
from core.validation import (
    sanitize_filename_prefix,
    validate_batch_pages,
    validate_webhook_url,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ScanRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=512)
    profile_id: str = Field(min_length=1, max_length=128)
    target_id: str = Field(min_length=1, max_length=128)
    source: str | None = Field(default=None, max_length=64)
    filename_prefix: str | None = Field(default=None, max_length=128)
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("filename_prefix")
    @classmethod
    def safe_filename(cls, value: str | None):
        return sanitize_filename_prefix(value) if value is not None else None

    @field_validator("webhook_url")
    @classmethod
    def safe_webhook(cls, value: str | None):
        return validate_webhook_url(value) if value else None


class BatchScanRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=512)
    profile_id: str = Field(min_length=1, max_length=128)
    target_id: str = Field(min_length=1, max_length=128)
    filename_prefix: str | None = Field(default=None, max_length=128)
    page_urls: List[str] = Field(min_length=1, max_length=100)

    @field_validator("filename_prefix")
    @classmethod
    def safe_filename(cls, value: str | None):
        return sanitize_filename_prefix(value, "batch_scan") if value is not None else None

    @model_validator(mode="after")
    def validate_pages(self):
        validate_batch_pages(self.page_urls)
        return self


class ScanPageRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=512)
    profile_id: str = Field(min_length=1, max_length=128)
    source: str | None = Field(default=None, max_length=64)


class PreviewScanRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=512)
    profile_id: str | None = Field(default=None, max_length=128)


class ScanProfile(BaseModel):
    id: str
    name: str
    dpi: int
    color_mode: str
    paper_size: str
    format: str
    quality: int
    source: str
    batch_scan: bool
    auto_detect: bool
    description: str


class ScanJobResponse(BaseModel):
    job_id: str
    status: JobStatus


def _get_scanner(device_id: str):
    device = DeviceRepository().get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    if device.device_type != "scanner":
        raise HTTPException(status_code=400, detail=f"Device '{device_id}' is not a scanner")
    return device


@router.get("/devices", response_model=List[dict])
async def list_devices():
    return ScannerManager().list_devices()


@router.get("/profiles", response_model=List[ScanProfile])
async def list_profiles():
    return ScannerManager().list_profiles()


@router.post("/start", response_model=ScanJobResponse)
async def start_scan(payload: ScanRequest):
    """Trigger a scan and enqueue delivery to the selected target."""
    device = _get_scanner(payload.device_id)
    try:
        job_id = ScannerManager().start_scan(
            device_id=device.uri,
            profile_id=payload.profile_id,
            target_id=payload.target_id,
            source=payload.source,
            filename_prefix=payload.filename_prefix,
            webhook_url=payload.webhook_url,
        )
        return ScanJobResponse(job_id=job_id, status=JobStatus.queued)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Scan start error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to start scan") from exc


@router.get("/jobs", response_model=List[JobRecord])
async def list_scan_jobs():
    return ScannerManager().list_jobs()


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_scan_job(job_id: str):
    job = ScannerManager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_scan_job(job_id: str):
    if not JobManager().cancel_job(job_id):
        raise HTTPException(
            status_code=400,
            detail="Job not found or cannot be cancelled (already completed/failed)",
        )
    return {"status": "cancelled", "job_id": job_id, "message": "Scan job has been cancelled"}


@router.get("/jobs/{job_id}/thumbnail")
async def get_job_thumbnail(job_id: str):
    job = JobManager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.thumbnail_path:
        thumbnail = Path(job.thumbnail_path)
        if thumbnail.exists():
            return FileResponse(thumbnail, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not available")


@router.post("/preview")
async def preview_scan(payload: PreviewScanRequest):
    """Perform a capped low-resolution preview scan."""
    device = _get_scanner(payload.device_id)
    profile = ScannerManager().resolve_profile(payload.profile_id)
    preview_file: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            preview_file = Path(tmp.name)
        cmd = [
            "scanimage",
            "--device-name",
            device.uri,
            "--resolution",
            str(min(profile["dpi"], 200)),
            "--mode",
            profile["color_mode"],
            "--format",
            "jpeg",
        ]
        with preview_file.open("wb") as output:
            result = subprocess.run(
                cmd, stdout=output, stderr=subprocess.PIPE, timeout=30
            )
        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise RuntimeError(f"scanimage failed: {error_msg}")
        image_data = base64.b64encode(preview_file.read_bytes()).decode("utf-8")
        return JSONResponse(
            {"status": "success", "image": f"data:image/jpeg;base64,{image_data}", "format": "jpeg"}
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Preview scan timed out") from exc
    except Exception as exc:
        logger.warning("Preview scan failed: %s", exc)
        raise HTTPException(status_code=500, detail="Preview scan failed") from exc
    finally:
        if preview_file:
            preview_file.unlink(missing_ok=True)


@router.post("/page")
async def scan_single_page(payload: ScanPageRequest):
    """Scan one page for the manual multi-page workflow."""
    device = _get_scanner(payload.device_id)
    profile = ScannerManager().resolve_profile(payload.profile_id)
    source = payload.source or profile.get("source", "Flatbed")
    page_file: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tiff", delete=False) as tmp:
            page_file = Path(tmp.name)
        cmd = [
            "scanimage",
            "--device-name",
            device.uri,
            "--resolution",
            str(profile.get("dpi", 200)),
            "--mode",
            profile.get("color_mode", "Gray"),
            "--format",
            "tiff",
        ]
        if source:
            cmd.extend(["--source", source])
        with page_file.open("wb") as output:
            result = subprocess.run(
                cmd, stdout=output, stderr=subprocess.PIPE, timeout=120
            )
        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise HTTPException(status_code=500, detail=f"Single page scan failed: {error_msg}")
        image_data = base64.b64encode(page_file.read_bytes()).decode("utf-8")
        return JSONResponse(
            {"status": "success", "image": f"data:image/tiff;base64,{image_data}", "format": "tiff"}
        )
    finally:
        if page_file:
            page_file.unlink(missing_ok=True)


@router.post("/batch", response_model=ScanJobResponse)
async def start_batch_scan(payload: BatchScanRequest):
    """Combine validated page images into one PDF and upload it."""
    _get_scanner(payload.device_id)
    profile = ScannerManager().resolve_profile(payload.profile_id)
    batch_id = str(uuid.uuid4())
    temp_dir = Path(tempfile.gettempdir()) / "scan2target_batch" / batch_id
    temp_dir.mkdir(parents=True, exist_ok=False)
    prefix = sanitize_filename_prefix(payload.filename_prefix, "batch_scan")
    pdf_file = temp_dir / f"{prefix}_{batch_id}.pdf"
    delivered = False
    job_id = str(uuid.uuid4())
    job_manager = JobManager()
    job_manager.create_job(
        job_id=job_id,
        job_type="scan",
        device_id=payload.device_id,
        target_id=payload.target_id,
        status=JobStatus.running,
    )

    images: list[Image.Image] = []
    try:
        for index, page_url in enumerate(payload.page_urls, start=1):
            if not page_url.startswith("data:image/") or "," not in page_url:
                raise ValueError(f"Invalid page data at position {index}")
            encoded = page_url.split(",", 1)[1]
            image_data = base64.b64decode(encoded, validate=True)
            with Image.open(BytesIO(image_data)) as source_image:
                source_image.load()
                images.append(source_image.convert("RGB"))

        quality = int(profile.get("quality", 85))
        dpi = float(profile.get("dpi", 200))
        images[0].save(
            pdf_file,
            save_all=True,
            append_images=images[1:],
            resolution=dpi,
            quality=quality,
        )

        job = job_manager.get_job(job_id)
        if job:
            job.file_path = str(pdf_file)
            job_manager.update_job(job)

        TargetManager().deliver(payload.target_id, str(pdf_file), {"job_id": job_id})
        delivered = True
        job = job_manager.get_job(job_id)
        if job:
            job.status = JobStatus.completed
            job.message = None
            job_manager.update_job(job)
        return ScanJobResponse(job_id=job_id, status=JobStatus.completed)
    except (ValueError, base64.binascii.Error, UnidentifiedImageError) as exc:
        job = job_manager.get_job(job_id)
        if job:
            job.status = JobStatus.failed
            job.message = "Invalid batch image data"
            job_manager.update_job(job)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        job = job_manager.get_job(job_id)
        if job:
            job.status = JobStatus.failed
            job.message = str(exc)
            job_manager.update_job(job)
        logger.error("Batch scan failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Batch scan failed") from exc
    finally:
        for image in images:
            image.close()
        if delivered:
            pdf_file.unlink(missing_ok=True)
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()
