"""Target and adapter configuration models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AdapterConfig(BaseModel):
    """Base config that preserves unknown fields for backward compatibility."""

    model_config = ConfigDict(extra="allow")


class SMBConfig(AdapterConfig):
    connection: str = Field(min_length=3)
    username: str = "guest"
    password: str = ""


class SFTPConfig(AdapterConfig):
    host: str = Field(min_length=1)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = "root"
    password: str = ""
    remote_path: str = "."
    strict_host_key_checking: bool = True


class EmailConfig(AdapterConfig):
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    to: str
    from_address: str = "scan2target@localhost"
    username: str | None = None
    password: str | None = None
    use_tls: bool = True


class PaperlessConfig(AdapterConfig):
    url: str
    api_token: str = Field(min_length=1)
    correspondent: int | None = None
    document_type: int | None = None
    tags: list[int] = Field(default_factory=list)


class WebhookConfig(AdapterConfig):
    url: str


class CloudTokenConfig(AdapterConfig):
    access_token: str = Field(min_length=1)
    path: str | None = None
    folder_id: str | None = None


class NextcloudConfig(AdapterConfig):
    url: str
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    path: str = "/Scans"


class TargetConfig(BaseModel):
    id: str
    type: str
    name: str
    config: dict[str, Any]
    enabled: bool = True
    description: Optional[str] = None
    is_favorite: bool = False
