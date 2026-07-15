"""Job manager with SQLite persistence and live lifecycle updates."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from core.jobs.models import JobRecord, JobStatus
from core.jobs.repository import JobRepository

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self):
        self.repo = JobRepository()

    def _broadcast_job_update(self, job: JobRecord):
        """Broadcast a complete job snapshot without blocking worker threads."""
        try:
            from core.websocket import get_connection_manager, get_main_loop

            manager = get_connection_manager()
            payload = {
                "id": job.id,
                "job_type": job.job_type,
                "status": job.status.value,
                "device_id": job.device_id,
                "target_id": job.target_id,
                "printer_id": job.printer_id,
                "file_path": job.file_path,
                "thumbnail_path": job.thumbnail_path,
                "message": job.message,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
                "last_error": job.last_error,
                "delivery_started_at": (
                    job.delivery_started_at.isoformat() if job.delivery_started_at else None
                ),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
            try:
                asyncio.get_running_loop()
                asyncio.create_task(manager.send_job_update(payload))
            except RuntimeError:
                main_loop = get_main_loop()
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        manager.send_job_update(payload), main_loop
                    )
        except Exception as exc:
            logger.error("WebSocket broadcast failed: %s", exc)

    def create_job(
        self,
        job_id: str,
        job_type: str,
        status: JobStatus,
        device_id: Optional[str] = None,
        target_id: Optional[str] = None,
        printer_id: Optional[str] = None,
        metadata: dict[str, Any] | None = None,
        max_retries: int = 5,
    ) -> JobRecord:
        now = datetime.now(timezone.utc)
        job = JobRecord(
            id=job_id,
            job_type=job_type,
            status=status,
            device_id=device_id,
            target_id=target_id,
            printer_id=printer_id,
            metadata=metadata or {},
            max_retries=max(0, max_retries),
            created_at=now,
            updated_at=now,
        )
        created = self.repo.create(job)
        self._broadcast_job_update(created)
        return created

    def update_job(self, job: JobRecord) -> JobRecord:
        updated = self.repo.update(job)
        self._broadcast_job_update(updated)
        return updated

    def transition(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str | None = None,
        last_error: str | None = None,
        next_retry_at: datetime | None = None,
    ) -> JobRecord | None:
        job = self.get_job(job_id)
        if not job:
            return None
        if job.status == JobStatus.cancelled and status != JobStatus.cancelled:
            return job
        job.status = status
        job.message = message
        job.last_error = last_error
        job.next_retry_at = next_retry_at
        now = datetime.now(timezone.utc)
        if status == JobStatus.delivering:
            job.delivery_started_at = now
        if status.terminal:
            job.completed_at = now
            job.next_retry_at = None
        return self.update_job(job)

    def list_jobs(
        self, job_type: Optional[str] = None, printer_id: Optional[str] = None
    ) -> List[JobRecord]:
        return self.repo.list(job_type=job_type, printer_id=printer_id)

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.repo.get(job_id)

    def list_history(self) -> List[JobRecord]:
        return self.repo.list()

    def list_delivery_attempts(self, job_id: str) -> list[dict]:
        return self.repo.list_delivery_attempts(job_id)

    def clear_completed_jobs(self) -> int:
        return self.repo.clear_completed()

    def delete_job(self, job_id: str) -> bool:
        return self.repo.delete(job_id)

    def cancel_job(self, job_id: str) -> bool:
        from core.worker import get_worker

        job = self.get_job(job_id)
        if not job or job.status.terminal:
            return False
        get_worker().cancel_task(job_id)
        job.status = JobStatus.cancelled
        job.message = "Job cancelled by user"
        job.next_retry_at = None
        job.completed_at = datetime.now(timezone.utc)
        self.update_job(job)
        return True
