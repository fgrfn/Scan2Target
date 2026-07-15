"""Job persistence models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"  # legacy compatibility for pre-4.1 records
    scanning = "scanning"
    processing = "processing"
    delivering = "delivering"
    retry_scheduled = "retry_scheduled"
    delivery_failed = "delivery_failed"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {
            JobStatus.completed,
            JobStatus.delivery_failed,
            JobStatus.failed,
            JobStatus.cancelled,
        }


class JobRecord(BaseModel):
    id: str
    job_type: str
    device_id: Optional[str] = None
    target_id: Optional[str] = None
    printer_id: Optional[str] = None
    status: JobStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 5
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    delivery_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
