import logging
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
from app.scanning.discovery import SCAN_PROFILES
import app.jobs.service as jobs_svc
from app.jobs.schemas import BatchRequest, ScanJobResponse, ScanRequest, JobOut
from app.jobs.worker import get_worker
from app.scanning.service import combine_batch, scan_and_deliver, scan_preview
import app.devices.service as dev_svc

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/profiles")
def list_profiles(_=_auth):
    return SCAN_PROFILES


@router.post("/start", response_model=ScanJobResponse)
async def start_scan(req: ScanRequest, _=_auth):
    dev = dev_svc.get_device(req.device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    valid_ids = {p["id"] for p in SCAN_PROFILES}
    if req.profile_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {req.profile_id}")
    job = jobs_svc.create_job(req.device_id, req.target_id)
    await get_worker().submit(
        job["id"],
        scan_and_deliver(job["id"], dev["uri"], req.profile_id,
                          req.target_id, req.filename_prefix, req.webhook_url),
    )
    return ScanJobResponse(job_id=job["id"])


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(_=_auth):
    return jobs_svc.list_jobs()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, _=_auth):
    j = jobs_svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, _=_auth):
    j = jobs_svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    cancelled = await get_worker().cancel(job_id)
    if cancelled or j["status"] in ("queued",):
        jobs_svc.update_status(job_id, "cancelled")
    return {"status": "cancelled", "job_id": job_id}


@router.post("/preview")
async def preview(body: dict, _=_auth):
    device_id = body.get("device_id")
    profile_id = body.get("profile_id", "gray_150_pdf")
    dev = dev_svc.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        image_b64 = await scan_preview(dev["uri"], profile_id)
        return {"status": "ok", "image": image_b64}
    except Exception as e:
        logger.error("Preview failed for device %s: %s", device_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Preview failed")


@router.post("/batch", response_model=ScanJobResponse)
async def batch_scan(req: BatchRequest, _=_auth):
    job = jobs_svc.create_job(req.device_id, req.target_id)
    await get_worker().submit(
        job["id"],
        combine_batch(job["id"], req.target_id, req.filename_prefix, req.page_paths),
    )
    return ScanJobResponse(job_id=job["id"])
