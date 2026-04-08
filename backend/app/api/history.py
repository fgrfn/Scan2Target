from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
import app.jobs.service as svc
from app.jobs.schemas import JobOut
from app.jobs.worker import get_worker

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/", response_model=list[JobOut])
def history(_=_auth):
    return svc.list_jobs(limit=500)


@router.delete("/")
def clear_history(_=_auth):
    count = svc.clear_completed()
    return {"status": "cleared", "deleted_count": count}


@router.delete("/{job_id}")
def delete_job(job_id: str, _=_auth):
    if not svc.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "deleted"}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, _=_auth):
    j = svc.get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    await get_worker().cancel(job_id)
    svc.update_status(job_id, "cancelled")
    return {"status": "cancelled"}


@router.post("/{job_id}/retry-upload")
async def retry_upload(job_id: str, _=_auth):
    j = svc.get_job(job_id)
    if not j or not j.get("file_path"):
        raise HTTPException(status_code=404, detail="Job or file not found")
    from pathlib import Path
    from app.targets.service import deliver
    import asyncio
    try:
        file_path = Path(j["file_path"])
        await asyncio.to_thread(deliver, j["target_id"], file_path, file_path.name)
        svc.update_status(job_id, "completed", message=None)
        return {"status": "delivered"}
    except Exception as e:
        svc.update_status(job_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))
