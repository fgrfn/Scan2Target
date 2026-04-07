from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    job_type: str = "scan"
    device_id: str | None = None
    target_id: str | None = None
    status: str
    file_path: str | None = None
    message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScanRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str = "scan"
    webhook_url: str | None = None


class BatchRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str = "scan"
    page_paths: list[str]   # local file paths from preview


class ScanJobResponse(BaseModel):
    job_id: str
    status: str = "queued"
