"""Unified history and delivery retry routes."""
from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from core.delivery.retry import get_delivery_retry_service
from core.jobs.manager import JobManager
from core.jobs.models import JobRecord

router = APIRouter()


@router.get("", response_model=List[JobRecord])
@router.get("/", response_model=List[JobRecord])
async def list_history():
    return JobManager().list_history()


@router.delete("/")
async def clear_history():
    deleted = JobManager().clear_completed_jobs()
    return {"status": "success", "deleted_count": deleted}


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    jobs = JobManager()
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.status.terminal:
        raise HTTPException(status_code=409, detail="Active jobs must be cancelled first")
    if job.file_path:
        Path(job.file_path).unlink(missing_ok=True)
    if job.thumbnail_path:
        Path(job.thumbnail_path).unlink(missing_ok=True)
    if not jobs.delete_job(job_id):
        raise HTTPException(status_code=500, detail="Failed to delete job")
    return {"status": "deleted", "job_id": job_id}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    jobs = JobManager()
    if not jobs.cancel_job(job_id):
        job = jobs.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=409, detail=f"Job cannot be cancelled ({job.status.value})")
    return {"status": "cancelled", "job_id": job_id}


@router.post("/{job_id}/retry-upload")
async def retry_upload(job_id: str):
    try:
        job = get_delivery_retry_service().enqueue_manual_retry(job_id)
        return {
            "status": job.status.value,
            "job_id": job.id,
            "next_retry_at": job.next_retry_at,
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{job_id}/delivery-attempts")
async def delivery_attempts(job_id: str):
    jobs = JobManager()
    if not jobs.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs.list_delivery_attempts(job_id)
