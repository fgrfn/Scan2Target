from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel

TARGET_TYPES = ["smb", "sftp", "email", "paperless", "webhook",
                "google_drive", "dropbox", "onedrive", "nextcloud"]


class TargetIn(BaseModel):
    type: str
    name: str
    config: dict[str, Any]
    enabled: bool = True
    description: str | None = None
    is_favorite: bool = False


class TargetOut(BaseModel):
    id: str
    type: str
    name: str
    config: dict[str, Any]   # sensitive fields are masked on output
    enabled: bool
    description: str | None = None
    is_favorite: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
