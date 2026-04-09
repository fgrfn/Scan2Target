"""Job persistence repository."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
import json

from core.database import get_db
from core.jobs.models import JobRecord, JobStatus


class JobRepository:
    """Repository for job persistence."""
    
    def __init__(self):
        self.db = get_db()
    
    def create(self, job: JobRecord) -> JobRecord:
        """Create a new job in the database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (id, job_type, device_id, target_id, printer_id, 
                                 status, file_path, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.job_type,
                job.device_id,
                job.target_id,
                job.printer_id,
                job.status.value,
                job.file_path,
                job.message,
                job.created_at.isoformat(),
                job.updated_at.isoformat()
            ))
        return job
    
    def get(self, job_id: str) -> Optional[JobRecord]:
        """Get a job by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                return JobRecord(
                    id=row['id'],
                    job_type=row['job_type'],
                    device_id=row['device_id'],
                    target_id=row['target_id'],
                    printer_id=row['printer_id'],
                    status=JobStatus(row['status']),
                    file_path=row['file_path'],
                    message=row['message'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
        return None
    
    def update(self, job: JobRecord) -> JobRecord:
        """Update an existing job."""
        job.updated_at = datetime.utcnow()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs 
                SET status = ?, file_path = ?, message = ?, updated_at = ?
                WHERE id = ?
            """, (
                job.status.value,
                job.file_path,
                job.message,
                job.updated_at.isoformat(),
                job.id
            ))
        return job
    
    def list(self, job_type: Optional[str] = None, 
             printer_id: Optional[str] = None,
             limit: int = 50) -> List[JobRecord]:
        """List jobs with optional filters."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
            
            if printer_id:
                query += " AND printer_id = ?"
                params.append(printer_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                JobRecord(
                    id=row['id'],
                    job_type=row['job_type'],
                    device_id=row['device_id'],
                    target_id=row['target_id'],
                    printer_id=row['printer_id'],
                    status=JobStatus(row['status']),
                    file_path=row['file_path'],
                    message=row['message'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
                for row in rows
            ]
    
    def delete(self, job_id: str) -> bool:
        """Delete a job."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0
    
    def clear_completed(self) -> int:
        """Delete all completed and failed jobs. Returns count of deleted jobs."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM jobs 
                WHERE status IN ('completed', 'failed')
            """)
            return cursor.rowcount
