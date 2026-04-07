"""Async job worker — processes scan jobs from a queue with bounded concurrency."""
from __future__ import annotations

import asyncio
import logging
from typing import Coroutine

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, concurrency: int = 2) -> None:
        self.concurrency = concurrency
        self._queue: asyncio.Queue[tuple[str, Coroutine]] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._running: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        self._tasks = [asyncio.create_task(self._loop(), name=f"worker-{i}")
                       for i in range(self.concurrency)]
        logger.info("Job worker started (%d workers)", self.concurrency)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Job worker stopped")

    async def submit(self, job_id: str, coro: Coroutine) -> None:
        await self._queue.put((job_id, coro))
        logger.debug("Job %s queued (queue size=%d)", job_id, self._queue.qsize())

    async def cancel(self, job_id: str) -> bool:
        task = self._running.get(job_id)
        if task:
            task.cancel()
            return True
        return False

    async def _loop(self) -> None:
        while True:
            job_id, coro = await self._queue.get()
            task = asyncio.create_task(coro, name=f"job-{job_id}")
            self._running[job_id] = task
            try:
                await task
            except asyncio.CancelledError:
                logger.info("Job %s cancelled", job_id)
            except Exception as exc:
                logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            finally:
                self._running.pop(job_id, None)
                self._queue.task_done()


_worker: JobWorker | None = None


def get_worker() -> JobWorker:
    global _worker
    if _worker is None:
        _worker = JobWorker()
    return _worker
