"""Guided UI capture endpoint tests."""
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


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
