"""Thread-safe registry for cancellable scanner subprocesses."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from typing import IO, Any, Sequence


class ScanCancelledError(RuntimeError):
    """Raised inside the scan worker after a user cancellation."""


class ProcessRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen] = {}
        self._cancelled: set[str] = set()

    def register(self, job_id: str, process: subprocess.Popen) -> None:
        with self._lock:
            if job_id in self._cancelled:
                self._terminate(process)
                raise ScanCancelledError("Scan cancelled by user")
            self._processes[job_id] = process

    def unregister(self, job_id: str, process: subprocess.Popen) -> None:
        with self._lock:
            if self._processes.get(job_id) is process:
                self._processes.pop(job_id, None)

    def cancel(self, job_id: str) -> bool:
        """Mark a job cancelled and terminate its active process if present."""
        with self._lock:
            self._cancelled.add(job_id)
            process = self._processes.get(job_id)
        if process is not None:
            self._terminate(process)
            return True
        return False

    def ensure_not_cancelled(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._cancelled:
                raise ScanCancelledError("Scan cancelled by user")

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancelled

    def finish(self, job_id: str) -> None:
        with self._lock:
            self._processes.pop(job_id, None)
            self._cancelled.discard(job_id)

    @staticmethod
    def _terminate(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=3)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass


_registry = ProcessRegistry()


def get_process_registry() -> ProcessRegistry:
    return _registry


def run_cancellable(
    job_id: str,
    args: Sequence[str],
    *,
    stdout: int | IO[Any] | None = None,
    stderr: int | IO[Any] | None = subprocess.PIPE,
    capture_output: bool = False,
    text: bool = False,
    timeout: float | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a process that can be terminated through ``cancel(job_id)``."""
    registry = get_process_registry()
    registry.ensure_not_cancelled(job_id)
    if capture_output:
        if stdout is not None or stderr not in (None, subprocess.PIPE):
            raise ValueError("stdout/stderr may not be supplied with capture_output")
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    process = subprocess.Popen(
        list(args),
        stdout=stdout,
        stderr=stderr,
        text=text,
        encoding=encoding,
        errors=errors,
        start_new_session=(os.name == "posix"),
    )
    registry.register(job_id, process)
    try:
        try:
            output, error = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            registry._terminate(process)
            output, error = process.communicate()
            raise subprocess.TimeoutExpired(args, timeout, output=output, stderr=error) from exc
        registry.ensure_not_cancelled(job_id)
        return subprocess.CompletedProcess(args, process.returncode, output, error)
    finally:
        registry.unregister(job_id, process)
