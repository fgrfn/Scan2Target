"""Persistent delivery retry queue tests."""
from __future__ import annotations

from pathlib import Path

import requests


def _service(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2TARGET_DATABASE_PATH", str(tmp_path / "scan2target.db"))
    monkeypatch.setenv("SCAN2TARGET_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SCAN2TARGET_RETRY_BASE_DELAY", "1")
    monkeypatch.setenv("SCAN2TARGET_RETRY_MAX_DELAY", "5")

    import core.database as database_module
    import core.delivery.retry as retry_module
    from core.config.settings import get_settings

    get_settings.cache_clear()
    database_module._db_instance = None
    retry_module._service = None
    return retry_module.DeliveryRetryService(), retry_module


def _create_delivery_job(service, tmp_path, max_retries=3):
    from core.jobs.models import JobStatus

    file = tmp_path / "scan.pdf"
    file.write_bytes(b"scan")
    job = service.jobs.create_job(
        job_id="job-1",
        job_type="scan",
        status=JobStatus.processing,
        target_id="target-1",
        max_retries=max_retries,
        metadata={"source": "test"},
    )
    job.file_path = str(file)
    service.jobs.update_job(job)
    return file


def test_transient_failure_is_persisted_then_completed(tmp_path, monkeypatch):
    service, retry_module = _service(tmp_path, monkeypatch)
    file = _create_delivery_job(service, tmp_path)

    def fail_once(*args, **kwargs):
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(retry_module.TargetManager, "deliver_once", fail_once)
    assert service.deliver_now("job-1") is False

    from core.jobs.models import JobStatus

    failed = service.jobs.get_job("job-1")
    assert failed.status == JobStatus.retry_scheduled
    assert failed.retry_count == 1
    assert failed.next_retry_at is not None
    assert file.exists()

    monkeypatch.setattr(retry_module.TargetManager, "deliver_once", lambda *args, **kwargs: None)
    assert service.deliver_now("job-1") is True
    completed = service.jobs.get_job("job-1")
    assert completed.status == JobStatus.completed
    assert not file.exists()
    assert [item["status"] for item in service.jobs.list_delivery_attempts("job-1")] == [
        "failed",
        "completed",
    ]


def test_permanent_failure_is_not_retried(tmp_path, monkeypatch):
    service, retry_module = _service(tmp_path, monkeypatch)
    file = _create_delivery_job(service, tmp_path)

    def fail_permanently(*args, **kwargs):
        raise ValueError("authentication failed")

    monkeypatch.setattr(retry_module.TargetManager, "deliver_once", fail_permanently)
    assert service.deliver_now("job-1") is False

    from core.jobs.models import JobStatus

    failed = service.jobs.get_job("job-1")
    assert failed.status == JobStatus.delivery_failed
    assert failed.next_retry_at is None
    assert file.exists()


def test_interrupted_delivery_is_requeued_after_restart(tmp_path, monkeypatch):
    service, _ = _service(tmp_path, monkeypatch)
    file = _create_delivery_job(service, tmp_path)

    from core.jobs.models import JobStatus

    service.jobs.transition("job-1", JobStatus.delivering, message="uploading")
    service.recover_interrupted_deliveries()
    recovered = service.jobs.get_job("job-1")
    assert recovered.status == JobStatus.retry_scheduled
    assert recovered.next_retry_at is not None
    assert Path(recovered.file_path) == file
