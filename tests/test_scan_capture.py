"""Guided UI capture endpoint tests."""
import asyncio
import base64
import re
from io import BytesIO
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image


def test_capture_pages_returns_complete_adf_stack(monkeypatch):
    from api import scan

    pages = ["data:image/jpeg;base64,Zmlyc3Q=", "data:image/jpeg;base64,c2Vjb25k"]
    calls = []

    monkeypatch.setattr(scan, "_get_scanner", lambda _device_id: SimpleNamespace(uri="sane:test"))

    def capture(_self, device_id, profile_id, source, batch):
        calls.append((device_id, profile_id, source, batch))
        return pages

    monkeypatch.setattr(scan.ScannerManager, "capture_pages", capture)
    app = FastAPI()
    app.include_router(scan.router, prefix="/api/v1/scan")

    response = TestClient(app).post(
        "/api/v1/scan/capture-pages",
        json={
            "device_id": "scanner-one",
            "profile_id": "document_300",
            "source": "ADF",
            "batch": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"pages": pages, "count": 2}
    assert calls == [("sane:test", "document_300", "ADF", True)]


def test_capture_pages_scans_exactly_one_adf_page(monkeypatch):
    from core.scanning import manager

    scanned = BytesIO()
    Image.new("RGB", (8, 12), "white").save(scanned, format="TIFF")
    commands = []

    monkeypatch.setattr(
        manager.ScannerManager,
        "resolve_profile",
        lambda _self, _profile_id: {"dpi": 200, "color_mode": "Gray", "quality": 80},
    )

    def run(command, *, stdout, stderr, timeout):
        commands.append(command)
        stdout.write(scanned.getvalue())
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(manager.subprocess, "run", run)
    pages = manager.ScannerManager().capture_pages(
        "sane:interactive-test",
        "document_300",
        source="ADF",
        batch=False,
    )

    assert len(pages) == 1
    assert pages[0].startswith("data:image/jpeg;base64,")
    assert "--source" in commands[0]
    assert commands[0][commands[0].index("--source") + 1] == "ADF"
    assert not any(argument.startswith("--batch") for argument in commands[0])


def test_capture_pages_reports_busy_scanner_as_conflict(monkeypatch):
    from api import scan

    monkeypatch.setattr(scan, "_get_scanner", lambda _device_id: SimpleNamespace(uri="sane:test"))
    monkeypatch.setattr(
        scan.ScannerManager,
        "capture_pages",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Scanner is busy")),
    )
    app = FastAPI()
    app.include_router(scan.router, prefix="/api/v1/scan")

    response = TestClient(app).post(
        "/api/v1/scan/capture-pages",
        json={"device_id": "scanner-one", "profile_id": "document_300", "source": "Flatbed"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Scanner is busy"}


def test_persistent_batch_combines_all_pages_into_one_pdf(tmp_path, monkeypatch):
    from api import batch_scan
    from api.scan import BatchScanRequest
    from core.config.settings import get_settings
    from core.jobs.models import JobStatus

    class MemoryJobs:
        records = {}

        def create_job(self, *, job_id, status, metadata, **kwargs):
            job = SimpleNamespace(
                id=job_id,
                status=status,
                file_path=None,
                metadata=metadata,
                **kwargs,
            )
            self.records[job_id] = job
            return job

        def get_job(self, job_id):
            return self.records.get(job_id)

        def update_job(self, job):
            self.records[job.id] = job
            return job

        def transition(self, job_id, status, **kwargs):
            job = self.records[job_id]
            job.status = status
            return job

    class Delivery:
        def deliver_now(self, job_id):
            MemoryJobs.records[job_id].status = JobStatus.completed
            return True

    def page_data(color):
        output = BytesIO()
        Image.new("RGB", (16, 24), color).save(output, format="JPEG")
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")

    monkeypatch.setenv("SCAN2TARGET_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(batch_scan, "_get_scanner", lambda _device_id: SimpleNamespace())
    monkeypatch.setattr(
        batch_scan.ScannerManager,
        "resolve_profile",
        lambda _self, _profile_id: {"dpi": 200, "quality": 85},
    )
    monkeypatch.setattr(batch_scan, "JobManager", MemoryJobs)
    monkeypatch.setattr(batch_scan, "get_delivery_retry_service", Delivery)

    response = asyncio.run(
        batch_scan.start_persistent_batch_scan(
            BatchScanRequest(
                device_id="scanner-one",
                profile_id="document_300",
                target_id="archive",
                filename_prefix="invoice",
                page_urls=[page_data("white"), page_data("black")],
            )
        )
    )

    job = MemoryJobs.records[response.job_id]
    pdf = tmp_path / "scans" / f"invoice_{response.job_id}.pdf"
    assert response.status == JobStatus.completed
    assert job.file_path == str(pdf)
    assert job.metadata["pages"] == 2
    assert pdf.read_bytes().startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())) == 2
    get_settings.cache_clear()


def test_batch_request_keeps_pdf_default_and_allows_jpeg():
    from api.scan import BatchScanRequest

    common = {
        "device_id": "scanner-one",
        "profile_id": "document_300",
        "target_id": "archive",
        "page_urls": ["data:image/jpeg;base64,ZmFrZQ=="],
    }
    assert BatchScanRequest(**common).output_format == "pdf"
    assert BatchScanRequest(**common, output_format="jpeg").output_format == "jpeg"
