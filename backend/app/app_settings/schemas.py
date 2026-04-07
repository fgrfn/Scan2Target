from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class SettingUpdate(BaseModel):
    value: Any


class SettingsOut(BaseModel):
    require_auth: bool = True
    log_level: str = "INFO"
    health_check_interval: int = 60
    scanner_check_interval: int = 30
    command_timeout: int = 15
    cors_origins: list[str] = ["*"]
