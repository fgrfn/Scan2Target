"""Job persistence repository."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from core.database import get_db
from core.jobs.models import JobRecord, JobStatus


class JobRepository:
    """Repository for job state, retries and delivery-attempt history."""

    def __init__(self):
        self.db = get_db()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    @classmethod
    def _row_to_job(cls, row) -> JobRecord:
        metadata_raw = row["metadata_json"] if "metadata_json" in row.keys() else "{}"
        try:
            metadata = json.loads(metadata_raw or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return JobRecord(
            id=row["id"],
            job_type=row["job_type"],
            device_id=row["device_id"],
            target_id=row["target_id"],
            printer_id=row["printer_id"],
            status=JobStatus(row["status"]),
            file_path=row["file_path"],
            thumbnail_path=row["thumbnail_path"] if "thumbnail_path" in row.keys() else None,
            message=row["message"],
            created_at=cls._parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=cls._parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
            retry_count=int(row["retry_count"] or 0),
            max_retries=int(row["max_retries"] or 5),
            next_retry_at=cls._parse_datetime(row["next_retry_at"]),
            last_error=row["last_error"],
            metadata=metadata,
            delivery_started_at=cls._parse_datetime(row["delivery_started_at"]),
            completed_at=cls._parse_datetime(row["completed_at"]),
        )

    def create(self, job: JobRecord) -> JobRecord:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, job_type, device_id, target_id, printer_id, status,
                    file_path, thumbnail_path, message, created_at, updated_at,
                    retry_count, max_retries, next_retry_at, last_error,
                    metadata_json, delivery_started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.job_type,
                    job.device_id,
                    job.target_id,
                    job.printer_id,
                    job.status.value,
                    job.file_path,
                    job.thumbnail_path,
                    job.message,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.retry_count,
                    job.max_retries,
                    job.next_retry_at.isoformat() if job.next_retry_at else None,
                    job.last_error,
                    json.dumps(job.metadata, separators=(",", ":")),
                    job.delivery_started_at.isoformat() if job.delivery_started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                ),
            )
        return job

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def update(self, job: JobRecord) -> JobRecord:
        job.updated_at = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE jobs SET
                    status = ?, file_path = ?, thumbnail_path = ?, message = ?,
                    updated_at = ?, retry_count = ?, max_retries = ?,
                    next_retry_at = ?, last_error = ?, metadata_json = ?,
                    delivery_started_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    job.status.value,
                    job.file_path,
                    job.thumbnail_path,
                    job.message,
                    job.updated_at.isoformat(),
                    job.retry_count,
                    job.max_retries,
                    job.next_retry_at.isoformat() if job.next_retry_at else None,
                    job.last_error,
                    json.dumps(job.metadata, separators=(",", ":")),
                    job.delivery_started_at.isoformat() if job.delivery_started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.id,
                ),
            )
        return job

    def list(
        self,
        job_type: Optional[str] = None,
        printer_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobRecord]:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list[object] = []
        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)
        if printer_id:
            query += " AND printer_id = ?"
            params.append(printer_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def list_due_retries(self, now: datetime, limit: int = 10) -> List[JobRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'retry_scheduled'
                  AND next_retry_at IS NOT NULL
                  AND next_retry_at <= ?
                ORDER BY next_retry_at ASC
                LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def list_interrupted_deliveries(self, limit: int = 100) -> List[JobRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = 'delivering' ORDER BY updated_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def record_delivery_attempt(
        self,
        job_id: str,
        attempt: int,
        status: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO delivery_attempts(
                    job_id, attempt, status, error, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    attempt,
                    status,
                    error,
                    started_at.isoformat(),
                    completed_at.isoformat() if completed_at else None,
                ),
            )

    def list_delivery_attempts(self, job_id: str) -> list[dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM delivery_attempts WHERE job_id = ? ORDER BY attempt ASC, id ASC",
                (job_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, job_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def clear_completed(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM jobs
                WHERE status IN ('completed', 'delivery_failed', 'failed', 'cancelled')
                """
            )
            return cursor.rowcount
