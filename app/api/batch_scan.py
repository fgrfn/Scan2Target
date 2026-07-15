"""Persistent manual multi-page scan route."""
from __future__ import annotations

import base64
import logging
import uuid
from io import BytesIO

from fastapi import APIRouter, HTTPException
from PIL import Image, UnidentifiedImageError

from api.scan import BatchScanRequest, ScanJobResponse, _get_scanner
from core.config.settings import get_settings
from core.delivery.retry import get_delivery_retry_service
from core.jobs.manager import JobManager
from core.jobs.models import JobStatus
from core.scanning.manager import ScannerManager
from core.validation import sanitize_filename_prefix

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/batch", response_model=ScanJobResponse)
async def start_persistent_batch_scan(payload: BatchScanRequest):
    """Combine pages into a restart-safe PDF and enqueue persistent delivery."""
    _get_scanner(payload.device_id)
    profile = ScannerManager().resolve_profile(payload.profile_id)
    settings = get_settings()
    job_id = str(uuid.uuid4())
    prefix = sanitize_filename_prefix(payload.filename_prefix, "batch_scan")
    output_dir = settings.data_dir / "scans"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = output_dir / f"{prefix}_{job_id}.pdf"
    jobs = JobManager()
    jobs.create_job(
        job_id=job_id,
        job_type="scan",
        device_id=payload.device_id,
        target_id=payload.target_id,
        status=JobStatus.processing,
        max_retries=settings.delivery_max_retries,
        metadata={
            "profile_id": payload.profile_id,
            "pages": len(payload.page_urls),
            "format": "pdf",
        },
    )

    images: list[Image.Image] = []
    try:
        for index, page_url in enumerate(payload.page_urls, start=1):
            if not page_url.startswith("data:image/") or "," not in page_url:
                raise ValueError(f"Invalid page data at position {index}")
            raw = base64.b64decode(page_url.split(",", 1)[1], validate=True)
            with Image.open(BytesIO(raw)) as source:
                source.load()
                images.append(source.convert("RGB"))
        images[0].save(
            pdf_file,
            save_all=True,
            append_images=images[1:],
            resolution=float(profile.get("dpi", 200)),
            quality=int(profile.get("quality", 85)),
        )
        job = jobs.get_job(job_id)
        if job:
            job.file_path = str(pdf_file)
            jobs.update_job(job)
        get_delivery_retry_service().deliver_now(job_id)
        final_job = jobs.get_job(job_id)
        return ScanJobResponse(
            job_id=job_id,
            status=final_job.status if final_job else JobStatus.failed,
        )
    except (ValueError, base64.binascii.Error, UnidentifiedImageError) as exc:
        pdf_file.unlink(missing_ok=True)
        jobs.transition(
            job_id,
            JobStatus.failed,
            message="Invalid batch image data",
            last_error=str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        job = jobs.get_job(job_id)
        if job and job.status not in {JobStatus.retry_scheduled, JobStatus.delivery_failed}:
            pdf_file.unlink(missing_ok=True)
            jobs.transition(job_id, JobStatus.failed, message=str(exc), last_error=str(exc))
        logger.error("Batch scan failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Batch scan failed") from exc
    finally:
        for image in images:
            image.close()
