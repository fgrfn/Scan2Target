"""Job manager with SQLite persistence."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
import asyncio

from core.jobs.models import JobRecord, JobStatus
from core.jobs.repository import JobRepository


class JobManager:
    def __init__(self):
        self.repo = JobRepository()
    
    def _broadcast_job_update(self, job: JobRecord):
        """Broadcast job update via WebSocket (non-blocking)."""
        try:
            from core.websocket import get_connection_manager
            manager = get_connection_manager()
            
            # Schedule the broadcast in the event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(manager.send_job_update({
                        "id": job.id,
                        "job_type": job.job_type,
                        "status": job.status.value,
                        "device_id": job.device_id,
                        "target_id": job.target_id,
                        "printer_id": job.printer_id,
                        "file_path": job.file_path,
                        "message": job.message,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    }))
            except RuntimeError:
                # No event loop running, skip broadcast
                pass
        except Exception as e:
            # Don't fail job updates if WebSocket broadcast fails
            print(f"WebSocket broadcast failed: {e}")

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
        created_job = self.repo.create(job)
        self._broadcast_job_update(created_job)
        return created_job
    
    def update_job(self, job: JobRecord) -> JobRecord:
        """Update job status and metadata."""
        updated_job = self.repo.update(job)
        self._broadcast_job_update(updated_job)
        return updated_job

    def list_jobs(self, job_type: Optional[str] = None, printer_id: Optional[str] = None) -> List[JobRecord]:
        return self.repo.list(job_type=job_type, printer_id=printer_id)

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.repo.get(job_id)

    def list_history(self) -> List[JobRecord]:
        return self.repo.list()
    
    def clear_completed_jobs(self) -> int:
        """Delete all completed and failed jobs from history."""
        return self.repo.clear_completed()
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a single job from history."""
        return self.repo.delete(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job."""
        from core.worker import get_worker
        
        job = self.get_job(job_id)
        if not job:
            return False
        
        # Only cancel if job is queued or running
        if job.status not in [JobStatus.queued, JobStatus.running]:
            return False
        
        # Try to cancel the background task
        worker = get_worker()
        worker.cancel_task(job_id)
        
        # Update job status
        job.status = JobStatus.cancelled
        job.message = "Job cancelled by user"
        self.update_job(job)
        
        return True
