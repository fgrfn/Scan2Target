"""Persistent delivery retry queue with exponential backoff."""
from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from core.config.settings import get_settings
from core.jobs.manager import JobManager
from core.jobs.models import JobRecord, JobStatus
from core.targets.manager import TargetManager

logger = logging.getLogger(__name__)


_PERMANENT_HINTS = (
    "authentication failed",
    "login failed",
    "access denied",
    "invalid token",
    "api token is missing",
    "unsupported target",
    "not found or disabled",
    "configuration",
    "missing recipient",
    "invalid smb",
)
_TRANSIENT_HINTS = (
    "timeout",
    "timed out",
    "temporarily unavailable",
    "connection reset",
    "connection refused",
    "host unreachable",
    "network is unreachable",
    "server error",
    "status 429",
    "status 500",
    "status 502",
    "status 503",
    "status 504",
)


def is_transient_delivery_error(exc: BaseException) -> bool:
    """Classify errors conservatively: only retry likely temporary failures."""
    if isinstance(
        exc,
        (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            subprocess.TimeoutExpired,
            TimeoutError,
            ConnectionError,
        ),
    ):
        return True
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code in {408, 425, 429} or (status_code and status_code >= 500):
            return True
        if status_code and 400 <= status_code < 500:
            return False
    message = str(exc).lower()
    if any(hint in message for hint in _PERMANENT_HINTS):
        return False
    return any(hint in message for hint in _TRANSIENT_HINTS)


class DeliveryRetryService:
    """Retry due deliveries and recover interrupted work after restarts."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.jobs = JobManager()
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._active_guard = threading.Lock()
        self._active_jobs: set[str] = set()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        await asyncio.to_thread(self.recover_interrupted_deliveries)
        self._task = asyncio.create_task(self._run(), name="delivery-retry-service")
        logger.info(
            "Delivery retry service started (interval=%ss)",
            self.settings.retry_poll_interval,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                due = self.jobs.repo.list_due_retries(datetime.now(timezone.utc), limit=10)
                for job in due:
                    await asyncio.to_thread(self.deliver_now, job.id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Delivery retry loop failed: %s", exc, exc_info=True)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self.settings.retry_poll_interval
                )
            except asyncio.TimeoutError:
                pass

    def recover_interrupted_deliveries(self) -> None:
        """Requeue jobs that were delivering when the process stopped."""
        now = datetime.now(timezone.utc)
        for job in self.jobs.repo.list_interrupted_deliveries():
            if job.file_path and Path(job.file_path).is_file():
                job.status = JobStatus.retry_scheduled
                job.message = "Delivery interrupted by restart; retry scheduled"
                job.next_retry_at = now
            else:
                job.status = JobStatus.delivery_failed
                job.message = "Delivery interrupted and local scan file is missing"
                job.last_error = job.message
                job.completed_at = now
            self.jobs.update_job(job)

    def enqueue_manual_retry(self, job_id: str) -> JobRecord:
        job = self.jobs.get_job(job_id)
        if not job:
            raise LookupError("Job not found")
        if not job.file_path or not Path(job.file_path).is_file():
            raise FileNotFoundError("Scan file no longer exists on disk")
        if not job.target_id:
            raise ValueError("Job has no target")
        job.status = JobStatus.retry_scheduled
        job.next_retry_at = datetime.now(timezone.utc)
        job.message = "Manual delivery retry scheduled"
        job.completed_at = None
        self.jobs.update_job(job)
        return job

    def deliver_now(self, job_id: str) -> bool:
        """Attempt one delivery and persist either success, retry or failure."""
        with self._active_guard:
            if job_id in self._active_jobs:
                return False
            self._active_jobs.add(job_id)
        try:
            job = self.jobs.get_job(job_id)
            if not job or job.status == JobStatus.cancelled:
                return False
            if not job.file_path or not Path(job.file_path).is_file():
                self.jobs.transition(
                    job_id,
                    JobStatus.delivery_failed,
                    message="Local scan file is missing",
                    last_error="Local scan file is missing",
                )
                return False
            if not job.target_id:
                self.jobs.transition(
                    job_id,
                    JobStatus.delivery_failed,
                    message="No delivery target configured",
                    last_error="No delivery target configured",
                )
                return False

            attempt = job.retry_count + 1
            started_at = datetime.now(timezone.utc)
            job.status = JobStatus.delivering
            job.delivery_started_at = started_at
            job.next_retry_at = None
            job.message = f"Delivery attempt {attempt}/{job.max_retries}"
            self.jobs.update_job(job)

            try:
                TargetManager().deliver_once(
                    job.target_id,
                    job.file_path,
                    {**job.metadata, "job_id": job.id, "delivery_attempt": attempt},
                )
            except Exception as exc:
                completed_at = datetime.now(timezone.utc)
                self.jobs.repo.record_delivery_attempt(
                    job.id,
                    attempt,
                    "failed",
                    started_at,
                    completed_at,
                    str(exc),
                )
                job = self.jobs.get_job(job.id) or job
                if job.status == JobStatus.cancelled:
                    return False
                job.retry_count = attempt
                job.last_error = str(exc)
                transient = is_transient_delivery_error(exc)
                if transient and attempt < job.max_retries:
                    delay = min(
                        self.settings.retry_max_delay,
                        self.settings.retry_base_delay * (2 ** max(0, attempt - 1)),
                    )
                    job.status = JobStatus.retry_scheduled
                    job.next_retry_at = completed_at + timedelta(seconds=delay)
                    job.message = f"Delivery failed; retry {attempt + 1} in {delay}s"
                    job.completed_at = None
                    logger.warning(
                        "Delivery for job %s failed; retry scheduled in %ss: %s",
                        job.id,
                        delay,
                        exc,
                    )
                else:
                    job.status = JobStatus.delivery_failed
                    job.next_retry_at = None
                    job.message = (
                        "Delivery failed permanently"
                        if not transient
                        else f"Delivery failed after {attempt} attempts"
                    )
                    job.completed_at = completed_at
                    logger.error("Delivery for job %s exhausted retries: %s", job.id, exc)
                self.jobs.update_job(job)
                return False

            completed_at = datetime.now(timezone.utc)
            self.jobs.repo.record_delivery_attempt(
                job.id, attempt, "completed", started_at, completed_at
            )
            job = self.jobs.get_job(job.id) or job
            if job.status == JobStatus.cancelled:
                return False
            job.status = JobStatus.completed
            job.message = None
            job.last_error = None
            job.next_retry_at = None
            job.completed_at = completed_at
            self.jobs.update_job(job)
            try:
                Path(job.file_path).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not remove delivered file %s: %s", job.file_path, exc)
            return True
        finally:
            with self._active_guard:
                self._active_jobs.discard(job_id)


_service: DeliveryRetryService | None = None


def get_delivery_retry_service() -> DeliveryRetryService:
    global _service
    if _service is None:
        _service = DeliveryRetryService()
    return _service
