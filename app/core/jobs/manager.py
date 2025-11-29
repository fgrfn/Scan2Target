"""In-memory job manager placeholder; replace with SQLite repository."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from app.core.jobs.models import JobRecord, JobStatus


class JobManager:
    def __init__(self):
        # In real implementation this would query SQLite
        self._jobs: dict[str, JobRecord] = {}

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
        self._jobs[job_id] = job
        return job

    def list_jobs(self, job_type: Optional[str] = None, printer_id: Optional[str] = None) -> List[JobRecord]:
        jobs = list(self._jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if printer_id:
            jobs = [j for j in jobs if j.printer_id == printer_id]
        return jobs

    def get_job(self, job_id: str) -> JobRecord:
        return self._jobs[job_id]

    def list_history(self) -> List[JobRecord]:
        return list(self._jobs.values())
