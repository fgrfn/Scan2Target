"""Background task worker for async job execution."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Dict

from core.jobs.manager import JobManager
from core.jobs.models import JobStatus
from core.scanning.process_registry import get_process_registry

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Execute long-running jobs without blocking FastAPI's event loop."""

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.job_manager = JobManager()

    def submit_task(self, job_id: str, coro: Callable) -> None:
        task = asyncio.create_task(self._execute_task(job_id, coro))
        self.tasks[job_id] = task

    async def _execute_task(self, job_id: str, coro: Callable) -> None:
        try:
            job = self.job_manager.get_job(job_id)
            if job and job.status == JobStatus.queued:
                job.status = JobStatus.running
                self.job_manager.update_job(job)

            await coro()

            # The scan implementation owns terminal states. Only complete a job
            # that is still running, never overwrite cancelled/failed records.
            job = self.job_manager.get_job(job_id)
            if job and job.status in (JobStatus.queued, JobStatus.running):
                job.status = JobStatus.completed
                self.job_manager.update_job(job)
        except asyncio.CancelledError:
            logger.info("Task %s cancelled", job_id)
            raise
        except Exception as exc:
            job = self.job_manager.get_job(job_id)
            if job and job.status != JobStatus.cancelled:
                job.status = JobStatus.failed
                job.message = f"Error: {exc}"
                self.job_manager.update_job(job)
            logger.error("Task %s failed: %s", job_id, exc, exc_info=True)
        finally:
            self.tasks.pop(job_id, None)

    def get_task_status(self, job_id: str) -> str:
        if job_id in self.tasks:
            task = self.tasks[job_id]
            if task.done():
                if task.cancelled():
                    return "cancelled"
                return "completed" if not task.exception() else "failed"
            return "running"
        return "not_found"

    async def wait_for_task(self, job_id: str, timeout: float = None) -> None:
        if job_id in self.tasks:
            try:
                await asyncio.wait_for(self.tasks[job_id], timeout=timeout)
            except asyncio.TimeoutError:
                pass

    def cancel_task(self, job_id: str) -> bool:
        """Terminate the active OS process and cancel its asyncio wrapper."""
        process_cancelled = get_process_registry().cancel(job_id)
        task_cancelled = False
        task = self.tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            task_cancelled = True
        return process_cancelled or task_cancelled


_worker_instance = None


def get_worker() -> BackgroundWorker:
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = BackgroundWorker()
    return _worker_instance
