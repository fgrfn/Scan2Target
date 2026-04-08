from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
import app.devices.service as svc
from app.devices.schemas import AddDeviceRequest, DeviceOut, DiscoveredDevice
from app.scanning.discovery import discover_all
from app.scanning.health import get_health_monitor

router = APIRouter()
_auth = Depends(get_current_user)


@router.get("/discover", response_model=list[DiscoveredDevice])
def discover(_=_auth):
    existing_uris = {d["uri"] for d in svc.list_devices()}
    found = discover_all()
    return [DiscoveredDevice(**d, already_added=(d["uri"] in existing_uris)) for d in found]


@router.get("", response_model=list[DeviceOut])
def list_devices(device_type: str | None = None, _=_auth):
    monitor = get_health_monitor()
    devices = svc.list_devices(device_type)
    result = []
    for d in devices:
        status = monitor.get_status(d["uri"])
        result.append(DeviceOut(**d, online=status.get("online")))
    return result


@router.post("", response_model=DeviceOut, status_code=201)
async def add_device(req: AddDeviceRequest, _=_auth):
    if svc.get_device_by_uri(req.uri):
        raise HTTPException(status_code=409, detail="Scanner with this URI already exists")
    device = svc.add_device(req.model_dump())
    # Immediately check online status so the UI shows correct state right away
    monitor = get_health_monitor()
    online = await monitor.check_now(device["uri"])
    return DeviceOut(**device, online=online)


@router.delete("/{device_id}")
def remove_device(device_id: str, _=_auth):
    if not svc.remove_device(device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "removed"}


@router.get("/health/status")
def health_status(_=_auth):
    return get_health_monitor().get_all_status()


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: str, _=_auth):
    d = svc.get_device(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    status = get_health_monitor().get_status(d["uri"])
    return DeviceOut(**d, online=status.get("online"))


@router.post("/{device_id}/favorite")
def set_favorite(device_id: str, body: dict, _=_auth):
    d = svc.set_favorite(device_id, body.get("is_favorite", False))
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "updated", "is_favorite": d["is_favorite"]}


@router.get("/{device_id}/check")
async def check_online(device_id: str, _=_auth):
    d = svc.get_device(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    online = await get_health_monitor().check_now(d["uri"])
    return {"device_id": device_id, "online": online}
