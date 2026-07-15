"""Cancellation tests for scanner subprocesses."""
from __future__ import annotations

import sys
import threading
import time
import uuid

from core.scanning.process_registry import (
    ScanCancelledError,
    get_process_registry,
    run_cancellable,
)


def test_cancel_terminates_active_process():
    job_id = str(uuid.uuid4())
    errors: list[BaseException] = []

    def target():
        try:
            run_cancellable(
                job_id,
                [sys.executable, "-c", "import time; time.sleep(30)"],
                timeout=35,
            )
        except BaseException as exc:  # captured for assertion in the test thread
            errors.append(exc)

    registry = get_process_registry()
    registry.finish(job_id)
    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not registry.has_active_process(job_id):
        time.sleep(0.05)

    assert registry.has_active_process(job_id)
    assert registry.cancel(job_id) is True
    thread.join(timeout=5)
    registry.finish(job_id)

    assert not thread.is_alive()
    assert any(isinstance(exc, ScanCancelledError) for exc in errors)
