"""Job manager with SQLite persistence."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from app.core.jobs.models import JobRecord, JobStatus
from app.core.jobs.repository import JobRepository


class JobManager:
    def __init__(self):
        self.repo = JobRepository()

    def create_job(
        self,
        job_id: str,
        job_type: str,
        status: JobStatus,
        device_id: Optional[str] = None,
        target_id: Optional[str] = None,
        printer_id: Optional[str] = None,
    ) -> JobRecord:
        job = JobRecord(
            id=job_id,
            job_type=job_type,
            status=status,
            device_id=device_id,
            target_id=target_id,
            printer_id=printer_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return self.repo.create(job)
    
    def update_job(self, job: JobRecord) -> JobRecord:
        """Update job status and metadata."""
        return self.repo.update(job)

    def list_jobs(self, job_type: Optional[str] = None, printer_id: Optional[str] = None) -> List[JobRecord]:
        return self.repo.list(job_type=job_type, printer_id=printer_id)

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.repo.get(job_id)

    def list_history(self) -> List[JobRecord]:
        return self.repo.list()
