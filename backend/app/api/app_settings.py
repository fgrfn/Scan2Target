from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import require_admin_or_open
from app.app_settings import service as svc
from app.app_settings.schemas import SettingUpdate, SettingsOut

router = APIRouter()
_admin = Depends(require_admin_or_open)


@router.get("", response_model=SettingsOut)
def get_settings(_=_admin):
    return SettingsOut(**svc.get_all())


@router.put("/{key}")
def update_setting(key: str, body: SettingUpdate, _=_admin):
    try:
        svc.set_setting(key, body.value)
        return {"key": key, "value": body.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
