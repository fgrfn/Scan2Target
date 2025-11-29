"""Scan-related API routes."""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.scanning.manager import ScannerManager
from app.core.jobs.models import JobStatus, JobRecord

router = APIRouter()


class ScanRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str | None = None


class ScanProfile(BaseModel):
    id: str
    dpi: int
    color_mode: str
    paper_size: str
    format: str


class ScanJobResponse(BaseModel):
    job_id: str
    status: JobStatus


@router.get("/devices", response_model=List[dict])
async def list_devices():
    """Return available scanners and capabilities."""
    return ScannerManager().list_devices()


@router.get("/profiles", response_model=List[ScanProfile])
async def list_profiles():
    """Return configured scan profiles."""
    return ScannerManager().list_profiles()


@router.post("/start", response_model=ScanJobResponse)
async def start_scan(payload: ScanRequest):
    """Trigger a scan and enqueue delivery to the selected target."""
    job_id = ScannerManager().start_scan(
        device_id=payload.device_id,
        profile_id=payload.profile_id,
        target_id=payload.target_id,
        filename_prefix=payload.filename_prefix,
    )
    return ScanJobResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/jobs", response_model=List[JobRecord])
async def list_scan_jobs():
    """Return recent scan jobs."""
    return ScannerManager().list_jobs()


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_scan_job(job_id: str):
    """Return a single scan job status."""
    return ScannerManager().get_job(job_id)
