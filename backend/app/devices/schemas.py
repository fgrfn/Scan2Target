from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class DeviceOut(BaseModel):
    id: str
    device_type: str = "scanner"
    name: str
    uri: str
    make: str | None = None
    model: str | None = None
    connection_type: str | None = None
    description: str | None = None
    is_active: bool = True
    is_favorite: bool = False
    last_seen: datetime | None = None
    online: bool | None = None


class DiscoveredDevice(BaseModel):
    uri: str
    name: str
    make: str | None = None
    model: str | None = None
    connection_type: str
    already_added: bool = False


class AddDeviceRequest(BaseModel):
    uri: str
    name: str
    device_type: str = "scanner"
    make: str | None = None
    model: str | None = None
    connection_type: str | None = None
    description: str | None = None
