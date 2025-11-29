"""Scanning orchestration and backend abstraction."""
from __future__ import annotations
from typing import List
import uuid

from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobRecord, JobStatus


class ScannerManager:
    """High-level entrypoint for scan operations."""

    def list_devices(self) -> List[dict]:
        # TODO: integrate SANE/eSCL discovery (Avahi + sane-airscan)
        return [
            {
                "id": "escl:HP_Envy_6400",
                "name": "HP Envy 6400",
                "capabilities": {"dpi": [150, 300, 600], "color_modes": ["color", "gray"], "sizes": ["A4", "Letter"]},
            }
        ]

    def list_profiles(self) -> List[dict]:
        # TODO: pull from config storage
        return [
            {"id": "scan_a4_color_300", "dpi": 300, "color_mode": "color", "paper_size": "A4", "format": "pdf"}
        ]

    def start_scan(self, device_id: str, profile_id: str, target_id: str, filename_prefix: str | None) -> str:
        job_id = str(uuid.uuid4())
        JobManager().create_job(
            job_id=job_id,
            job_type="scan",
            device_id=device_id,
            target_id=target_id,
            status=JobStatus.queued,
        )
        # TODO: dispatch actual scan execution to background worker
        return job_id

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def get_job(self, job_id: str) -> JobRecord:
        return JobManager().get_job(job_id)
