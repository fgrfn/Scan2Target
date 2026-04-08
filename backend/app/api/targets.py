from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth.dependencies import get_current_user
import app.targets.service as svc
from app.targets.schemas import TargetIn, TargetOut

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/browse-path")
def browse_path(path: str = Query(default=""), _=_auth):
    """List subdirectories for the local-folder path browser.

    Access is restricted to the configured data_dir (''/data'' by default)
    to prevent arbitrary filesystem traversal.
    """
    from pathlib import Path as _Path
    from app.config import get_settings

    data_dir = _Path(get_settings().data_dir).resolve()

    # Default to data_dir when no path supplied
    requested = _Path(path).resolve() if path else data_dir

    # Security: must stay within data_dir
    if not (requested == data_dir or requested.is_relative_to(data_dir)):
        raise HTTPException(status_code=403, detail="Path is outside the allowed data directory")

    if not requested.exists():
        # If the path doesn't exist yet, show parent so user can see context
        requested = data_dir

    if not requested.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    parent = None
    if requested != data_dir and requested.parent.is_relative_to(data_dir):
        parent = str(requested.parent)
    elif requested != data_dir:
        parent = str(data_dir)

    try:
        items = sorted(
            [{"name": item.name, "path": str(item)} for item in requested.iterdir() if item.is_dir()],
            key=lambda x: x["name"].lower(),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading directory")

    return {
        "root": str(data_dir),
        "current": str(requested),
        "parent": parent,
        "items": items,
    }


@router.get("", response_model=list[TargetOut])
def list_targets(_=_auth):
    return svc.list_targets()


@router.post("", response_model=TargetOut, status_code=201)
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
        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/{target_id}/favorite")
def set_favorite(target_id: str, body: dict, _=_auth):
    t = svc.set_favorite(target_id, body.get("is_favorite", False))
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"status": "updated", "is_favorite": t["is_favorite"]}
