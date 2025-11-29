from fastapi.testclient import TestClient

from app.main import create_app
from app.core.jobs.manager import JobManager


client = TestClient(create_app())


def setup_function():
    JobManager().reset_jobs()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan_flow_creates_job_and_lists_history():
    devices = client.get("/api/v1/scan/devices").json()
    assert devices, "expected at least one example scanner"

    profiles = client.get("/api/v1/scan/profiles").json()
    assert profiles, "expected at least one example profile"

    payload = {
        "device_id": devices[0]["id"],
        "profile_id": profiles[0]["id"],
        "target_id": "local_default",
    }
    start_resp = client.post("/api/v1/scan/start", json=payload)
    assert start_resp.status_code == 200
    body = start_resp.json()
    assert body["job_id"]
    assert body["status"] == "queued"

    jobs = client.get("/api/v1/scan/jobs").json()
    assert len(jobs) == 1

    history = client.get("/api/v1/history/").json()
    assert len(history) == 1
    assert history[0]["job_type"] == "scan"


def test_printer_test_page_records_job():
    printers = client.get("/api/v1/printers/").json()
    assert printers, "expected at least one example printer"
    printer_id = printers[0]["id"]

    resp = client.post(f"/api/v1/printers/{printer_id}/test")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    assert job_id

    jobs = client.get(f"/api/v1/printers/{printer_id}/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id
    assert jobs[0]["job_type"] == "print"
