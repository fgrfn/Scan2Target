"""Job persistence and lifecycle management."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.database import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(r: Any) -> dict:
    return dict(r)


def create_job(device_id: str | None, target_id: str | None,
               job_type: str = "scan",
               filename_prefix: str | None = None,
               profile_id: str | None = None) -> dict:
    job_id = str(uuid.uuid4())
    with get_db().connection() as conn:
        conn.execute(
            "INSERT INTO jobs (id, job_type, device_id, target_id, status, "
            "filename_prefix, profile_id, created_at, updated_at) "
            "VALUES (?,?,?,?,'queued',?,?,?,?)",
            (job_id, job_type, device_id, target_id,
             filename_prefix, profile_id, _now(), _now()),
        )
    return get_job(job_id)


def get_job(job_id: str) -> dict | None:
    with get_db().connection() as conn:
        r = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _row(r) if r else None


def list_jobs(limit: int = 100) -> list[dict]:
    with get_db().connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def update_status(job_id: str, status: str, message: str | None = None,
                  file_path: str | None = None) -> dict | None:
    now = _now()
    with get_db().connection() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, message=?, file_path=COALESCE(?,file_path), updated_at=? WHERE id=?",
            (status, message, file_path, now, job_id),
        )
    return get_job(job_id)


def delete_job(job_id: str) -> bool:
    with get_db().connection() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    return cur.rowcount > 0


def clear_completed() -> int:
    with get_db().connection() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE status IN ('completed','failed','cancelled')")
    return cur.rowcount
