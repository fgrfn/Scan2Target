"""Persistent scan-session lifecycle tests."""
from __future__ import annotations

import base64
import re
import shutil
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


def _image_data(color: str = "black") -> str:
    output = BytesIO()
    Image.new("RGB", (24, 32), color).save(output, "JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _service(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2TARGET_DATABASE_PATH", str(tmp_path / "scan2target.db"))
    monkeypatch.setenv("SCAN2TARGET_DATA_DIR", str(tmp_path / "data"))

    import core.database as database_module
    from core.config.settings import get_settings
    from core.scanning.sessions import ScanSessionService

    get_settings.cache_clear()
    database_module._db_instance = None
    return ScanSessionService()


def _create(service, mode="interactive"):
    return service.create(
        device_id="scanner-one",
        device_uri="sane:test",
        profile_id="document_300",
        target_id="archive",
        source="ADF" if mode == "automatic" else "Flatbed",
        capture_mode=mode,
    )


def test_session_pages_survive_service_recreation(tmp_path, monkeypatch):
    from core.scanning.sessions import ScanSessionService, ScannerManager

    service = _service(tmp_path, monkeypatch)
    session = _create(service)
    monkeypatch.setattr(
        ScannerManager,
        "capture_pages",
        lambda *_args, **_kwargs: [_image_data("red"), _image_data("blue")],
    )

    captured = service.capture(session.id)
    restored = ScanSessionService().get(session.id)

    assert len(captured.pages) == 2
    assert [page.id for page in restored.pages] == [page.id for page in captured.pages]
    assert all(service.page_path(session.id, page.id).is_file() for page in restored.pages)
    assert service.page_preview(session.id, restored.pages[0].id).startswith(b"\xff\xd8")


def test_automatic_adf_uses_batch_and_session_can_be_reordered(tmp_path, monkeypatch):
    from core.scanning.sessions import ScannerManager

    service = _service(tmp_path, monkeypatch)
    session = _create(service, mode="automatic")
    calls = []

    def capture(_self, device_uri, profile_id, source, batch, cancellation_id=None):
        calls.append((device_uri, profile_id, source, batch, cancellation_id))
        return [_image_data("red"), _image_data("blue")]

    monkeypatch.setattr(ScannerManager, "capture_pages", capture)
    captured = service.capture(session.id)
    reversed_ids = [page.id for page in reversed(captured.pages)]
    reordered = service.reorder(session.id, reversed_ids)
    rotated = service.rotate(session.id, reordered.pages[0].id)
    reduced = service.remove_page(session.id, rotated.pages[1].id)

    assert calls == [("sane:test", "document_300", "ADF", True, session.id)]
    assert [page.id for page in reordered.pages] == reversed_ids
    assert len(reduced.pages) == 1


def test_cancel_removes_session_files(tmp_path, monkeypatch):
    from core.scanning.sessions import ScannerManager

    service = _service(tmp_path, monkeypatch)
    session = _create(service)
    monkeypatch.setattr(
        ScannerManager,
        "capture_pages",
        lambda *_args, **_kwargs: [_image_data()],
    )
    service.capture(session.id)
    session_dir = service.root / session.id

    service.cancel(session.id)

    assert not session_dir.exists()
    assert service.list_active() == []


def test_interrupted_processing_session_is_resumable_after_restart(tmp_path, monkeypatch):
    from core.jobs.manager import JobManager
    from core.jobs.models import JobStatus

    service = _service(tmp_path, monkeypatch)
    session = _create(service)
    jobs = JobManager()
    jobs.create_job(
        job_id="interrupted-job",
        job_type="scan",
        status=JobStatus.processing,
        metadata={"session_id": session.id},
    )
    with service.db.get_connection() as conn:
        conn.execute(
            "UPDATE scan_sessions SET status = 'processing' WHERE id = ?",
            (session.id,),
        )

    assert service.recover_interrupted() == 1
    assert service.get(session.id).status == "active"
    assert jobs.get_job("interrupted-job").status == JobStatus.failed


def test_finalize_optimizes_ocr_and_creates_one_pdf(tmp_path, monkeypatch):
    import core.scanning.sessions as sessions_module
    from core.jobs.manager import JobManager
    from core.jobs.models import JobStatus

    service = _service(tmp_path, monkeypatch)
    session = _create(service)
    monkeypatch.setattr(
        sessions_module.ScannerManager,
        "capture_pages",
        lambda *_args, **_kwargs: [_image_data("black"), _image_data("white")],
    )
    monkeypatch.setattr(
        sessions_module.ScannerManager,
        "resolve_profile",
        lambda _self, _profile_id: {"dpi": 200, "quality": 85},
    )
    service.capture(session.id)
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        shutil.copyfile(command[-2], command[-1])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    class Delivery:
        def deliver_now(self, job_id):
            JobManager().transition(job_id, JobStatus.completed)
            return True

    monkeypatch.setattr(sessions_module.subprocess, "run", run)
    monkeypatch.setattr(sessions_module, "get_delivery_retry_service", Delivery)

    result = service.finalize(
        session.id,
        target_id="archive",
        filename_prefix="invoice",
        optimize=True,
        remove_blank_pages=True,
        ocr=True,
        pdfa=True,
        ocr_language="deu+eng",
    )

    job = JobManager().get_job(result.job_id)
    pdf = Path(job.file_path)
    assert result.status == JobStatus.completed
    assert job.metadata["pages"] == 1
    assert pdf.read_bytes().startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())) == 1
    assert "--deskew" in commands[0]
    assert commands[0][commands[0].index("--output-type") + 1] == "pdfa-2"
    assert service.get(session.id).status == "completed"
    assert not (service.root / session.id).exists()
