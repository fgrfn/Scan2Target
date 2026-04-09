"""Job persistence models."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobRecord(BaseModel):
    id: str
    job_type: str
    device_id: Optional[str] = None
    target_id: Optional[str] = None
    printer_id: Optional[str] = None
    status: JobStatus
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    file_path: Optional[str] = None
    message: Optional[str] = None
    thumbnail_path: Optional[str] = None
