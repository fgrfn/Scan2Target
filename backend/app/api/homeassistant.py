"""Home Assistant integration endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.scanning.discovery import SCAN_PROFILES
import app.devices.service as dev_svc
import app.targets.service as tgt_svc
import app.jobs.service as jobs_svc
from app.jobs.worker import get_worker
from app.scanning.service import scan_and_deliver
from pydantic import BaseModel

router = APIRouter()
_auth = Depends(get_current_user)


class HAScanRequest(BaseModel):
    scanner_id: str = "favorite"
    target_id: str = "favorite"
    profile: str = "doc_200_gray_pdf"
    filename: str = "ha_scan"


@router.post("/scan")
async def ha_scan(req: HAScanRequest, _=_auth):
    # Resolve scanner
    if req.scanner_id == "favorite":
        devs = [d for d in dev_svc.list_devices() if d.get("is_favorite")]
        if not devs:
            raise HTTPException(status_code=400, detail="No favorite scanner configured")
        dev = devs[0]
    else:
        dev = dev_svc.get_device(req.scanner_id)
        if not dev:
            raise HTTPException(status_code=404, detail="Scanner not found")

    # Resolve target
    if req.target_id == "favorite":
        tgt = tgt_svc.get_favorite_target()
        if not tgt:
            raise HTTPException(status_code=400, detail="No favorite target configured")
        target_id = tgt["id"]
    else:
        target_id = req.target_id

    job = jobs_svc.create_job(dev["id"], target_id)
    await get_worker().submit(
        job["id"],
        scan_and_deliver(job["id"], dev["uri"], req.profile,
                          target_id, req.filename, None),
    )
    return {"status": "queued", "job_id": job["id"]}


@router.get("/status")
def ha_status(_=_auth):
    devices = dev_svc.list_devices()
    targets = tgt_svc.list_targets()
    jobs = jobs_svc.list_jobs(limit=10)
    running = [j for j in jobs if j["status"] == "running"]
    return {
        "scanners_count": len(devices),
        "targets_count": len(targets),
        "running_jobs": len(running),
        "last_job_status": jobs[0]["status"] if jobs else None,
    }


@router.get("/scanners")
def ha_scanners(_=_auth):
    return {"scanners": [{"id": d["id"], "name": d["name"], "is_favorite": d["is_favorite"]}
                          for d in dev_svc.list_devices()]}


@router.get("/targets")
def ha_targets(_=_auth):
    return {"targets": [{"id": t["id"], "name": t["name"], "type": t["type"],
                          "is_favorite": t["is_favorite"]}
                         for t in tgt_svc.list_targets()]}


@router.get("/profiles")
def ha_profiles(_=_auth):
    return {"profiles": [{"id": p["id"], "name": p["name"], "source": p["source"]}
                          for p in SCAN_PROFILES]}
