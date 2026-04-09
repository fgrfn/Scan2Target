"""Background task worker for async job execution."""
from __future__ import annotations
import asyncio
import logging
from typing import Callable, Dict, Any
from datetime import datetime
import traceback

from core.jobs.manager import JobManager
from core.jobs.models import JobStatus

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Background worker for executing long-running tasks.
    
    Uses asyncio for async execution without blocking the API.
    For production, consider using Celery or RQ for distributed processing.
    """
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.job_manager = JobManager()
    
    def submit_task(self, job_id: str, coro: Callable) -> None:
        """
        Submit a coroutine for background execution.
        
        Args:
            job_id: Job ID for tracking
            coro: Async coroutine to execute
        """
        task = asyncio.create_task(self._execute_task(job_id, coro))
        self.tasks[job_id] = task
    
    async def _execute_task(self, job_id: str, coro: Callable) -> None:
        """Execute task with error handling and status updates."""
        try:
            # Update job to running
            job = self.job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.running
                self.job_manager.update_job(job)
            
            # Execute the task
            await coro()
            
            # Update job to completed
            job = self.job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.completed
                self.job_manager.update_job(job)
                
        except Exception as e:
            # Update job to failed
            job = self.job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.failed
                job.message = f"Error: {str(e)}"
                self.job_manager.update_job(job)
            
            logger.error(f"Task {job_id} failed: {e}", exc_info=True)
        
        finally:
            # Clean up task reference
            self.tasks.pop(job_id, None)
    
    def get_task_status(self, job_id: str) -> str:
        """Get the status of a background task."""
        if job_id in self.tasks:
            task = self.tasks[job_id]
            if task.done():
                return "completed" if not task.exception() else "failed"
            return "running"
        return "not_found"
    
    async def wait_for_task(self, job_id: str, timeout: float = None) -> None:
        """Wait for a specific task to complete."""
        if job_id in self.tasks:
            try:
                await asyncio.wait_for(self.tasks[job_id], timeout=timeout)
            except asyncio.TimeoutError:
                pass
    
    def cancel_task(self, job_id: str) -> bool:
        """Cancel a running background task."""
        if job_id in self.tasks:
            task = self.tasks[job_id]
            if not task.done():
                task.cancel()
                self.tasks.pop(job_id, None)
                return True
        return False


# Global worker instance
_worker_instance = None


def get_worker() -> BackgroundWorker:
    """Get or create the global background worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = BackgroundWorker()
    return _worker_instance
