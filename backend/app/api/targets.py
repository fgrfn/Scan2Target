from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
import app.targets.service as svc
from app.targets.schemas import TargetIn, TargetOut

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/", response_model=list[TargetOut])
def list_targets(_=_auth):
    return svc.list_targets()


@router.post("/", response_model=TargetOut, status_code=201)
def create_target(body: TargetIn, _=_auth):
    try:
        svc.test_config(body.type, body.config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {e}")
    return svc.create_target(body.model_dump())


@router.put("/{target_id}", response_model=TargetOut)
def update_target(target_id: str, body: TargetIn, _=_auth):
    try:
        svc.test_config(body.type, body.config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {e}")
    result = svc.update_target(target_id, body.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    return result


@router.delete("/{target_id}")
def delete_target(target_id: str, _=_auth):
    if not svc.delete_target(target_id):
        raise HTTPException(status_code=404, detail="Target not found")
    return {"status": "deleted", "target_id": target_id}


@router.post("/{target_id}/test")
def test_target(target_id: str, _=_auth):
    try:
        svc.test_target(target_id)
        return {"target_id": target_id, "status": "ok", "message": "Connection successful"}
    except Exception as e:
        return {"target_id": target_id, "status": "error", "message": str(e)}


@router.post("/{target_id}/favorite")
def set_favorite(target_id: str, body: dict, _=_auth):
    t = svc.set_favorite(target_id, body.get("is_favorite", False))
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"status": "updated", "is_favorite": t["is_favorite"]}
