"""Persistent server-side scan sessions and document finalization."""
from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, ImageOps, ImageStat
from pydantic import BaseModel, Field

from core.config.settings import get_settings
from core.database import get_db
from core.delivery.retry import get_delivery_retry_service
from core.jobs.manager import JobManager
from core.jobs.models import JobStatus
from core.scanning.manager import ScannerManager
from core.scanning.process_registry import get_process_registry
from core.validation import sanitize_filename_prefix

logger = logging.getLogger(__name__)

CaptureMode = Literal["interactive", "automatic"]
SessionStatus = Literal["active", "processing", "completed", "cancelled"]


class ScanSessionPage(BaseModel):
    id: str
    position: int
    preview_url: str
    created_at: datetime


class ScanSession(BaseModel):
    id: str
    device_id: str
    profile_id: str
    target_id: str | None = None
    source: str
    capture_mode: CaptureMode
    status: SessionStatus
    options: dict = Field(default_factory=dict)
    pages: list[ScanSessionPage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FinalizeResult(BaseModel):
    job_id: str
    status: JobStatus


class ScanSessionService:
    """Store captured pages outside the browser until final delivery."""

    def __init__(self) -> None:
        self.db = get_db()
        self.settings = get_settings()
        self.root = self.settings.data_dir / "scan-sessions"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _decode_options(raw: str | None) -> dict:
        try:
            return json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def _page_from_row(self, row) -> ScanSessionPage:
        return ScanSessionPage(
            id=row["id"],
            position=int(row["position"]),
            preview_url=f"/api/v1/scan/sessions/{row['session_id']}/pages/{row['id']}/image",
            created_at=self._parse_datetime(row["created_at"]),
        )

    def _session_from_row(self, row, page_rows) -> ScanSession:
        return ScanSession(
            id=row["id"],
            device_id=row["device_id"],
            profile_id=row["profile_id"],
            target_id=row["target_id"],
            source=row["source"],
            capture_mode=row["capture_mode"],
            status=row["status"],
            options=self._decode_options(row["options_json"]),
            pages=[self._page_from_row(page) for page in page_rows],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
        )

    def create(
        self,
        *,
        device_id: str,
        device_uri: str,
        profile_id: str,
        target_id: str | None,
        source: str,
        capture_mode: CaptureMode,
        options: dict | None = None,
    ) -> ScanSession:
        session_id = str(uuid.uuid4())
        now = self._now().isoformat()
        self._session_dir(session_id).mkdir(parents=True, exist_ok=False)
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scan_sessions (
                    id, device_id, device_uri, profile_id, target_id, source,
                    capture_mode, status, options_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    session_id,
                    device_id,
                    device_uri,
                    profile_id,
                    target_id,
                    source,
                    capture_mode,
                    json.dumps(options or {}, separators=(",", ":")),
                    now,
                    now,
                ),
            )
        return self.get(session_id)

    def get(self, session_id: str) -> ScanSession:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                raise LookupError("Scan session not found")
            pages = conn.execute(
                "SELECT * FROM scan_session_pages WHERE session_id = ? ORDER BY position",
                (session_id,),
            ).fetchall()
        return self._session_from_row(row, pages)

    def list_active(self) -> list[ScanSession]:
        self.cleanup_expired()
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM scan_sessions WHERE status = 'active' ORDER BY updated_at DESC"
            ).fetchall()
        return [self.get(row["id"]) for row in rows]

    def _raw_session(self, session_id: str):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if not row:
            raise LookupError("Scan session not found")
        if row["status"] != "active":
            raise ValueError(f"Scan session is {row['status']}")
        return row

    def capture(self, session_id: str) -> ScanSession:
        row = self._raw_session(session_id)
        batch = row["capture_mode"] == "automatic" and row["source"].lower().startswith("adf")
        pages = ScannerManager().capture_pages(
            row["device_uri"],
            row["profile_id"],
            row["source"],
            batch,
            cancellation_id=session_id,
        )
        self._raw_session(session_id)
        current_count = len(self.get(session_id).pages)
        if current_count + len(pages) > self.settings.max_batch_pages:
            raise ValueError(
                f"A scan session may contain at most {self.settings.max_batch_pages} pages"
            )
        session_dir = self._session_dir(session_id)
        created_paths: list[Path] = []
        try:
            with self.db.get_connection() as conn:
                next_position = int(
                    conn.execute(
                        "SELECT COALESCE(MAX(position), 0) + 1 FROM scan_session_pages WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()[0]
                )
                now = self._now().isoformat()
                for offset, data_url in enumerate(pages):
                    page_id = str(uuid.uuid4())
                    encoded = data_url.split(",", 1)[1]
                    raw = base64.b64decode(encoded, validate=True)
                    page_path = session_dir / f"{page_id}.jpg"
                    with Image.open(BytesIO(raw)) as image:
                        ImageOps.exif_transpose(image).convert("RGB").save(
                            page_path, "JPEG", quality=92, optimize=True
                        )
                    created_paths.append(page_path)
                    conn.execute(
                        """
                        INSERT INTO scan_session_pages(id, session_id, position, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (page_id, session_id, next_position + offset, str(page_path), now),
                    )
                conn.execute(
                    "UPDATE scan_sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id),
                )
        except Exception:
            for path in created_paths:
                path.unlink(missing_ok=True)
            raise
        return self.get(session_id)

    def page_path(self, session_id: str, page_id: str) -> Path:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT file_path FROM scan_session_pages WHERE id = ? AND session_id = ?",
                (page_id, session_id),
            ).fetchone()
        if not row:
            raise LookupError("Scan page not found")
        path = Path(row["file_path"])
        if not path.is_file():
            raise FileNotFoundError("Scan page file is missing")
        return path

    def page_preview(self, session_id: str, page_id: str) -> bytes:
        path = self.page_path(session_id, page_id)
        with Image.open(path) as image:
            preview = ImageOps.exif_transpose(image).convert("RGB")
            preview.thumbnail((480, 640))
            output = BytesIO()
            preview.save(output, "JPEG", quality=82, optimize=True)
        return output.getvalue()

    def remove_page(self, session_id: str, page_id: str) -> ScanSession:
        self._raw_session(session_id)
        path = self.page_path(session_id, page_id)
        with self.db.get_connection() as conn:
            conn.execute(
                "DELETE FROM scan_session_pages WHERE id = ? AND session_id = ?",
                (page_id, session_id),
            )
            self._compact_positions(conn, session_id)
            conn.execute(
                "UPDATE scan_sessions SET updated_at = ? WHERE id = ?",
                (self._now().isoformat(), session_id),
            )
        path.unlink(missing_ok=True)
        return self.get(session_id)

    @staticmethod
    def _compact_positions(conn, session_id: str) -> None:
        rows = conn.execute(
            "SELECT id FROM scan_session_pages WHERE session_id = ? ORDER BY position",
            (session_id,),
        ).fetchall()
        for position, row in enumerate(rows, start=1):
            conn.execute(
                "UPDATE scan_session_pages SET position = ? WHERE id = ?",
                (-position, row["id"]),
            )
        conn.execute(
            "UPDATE scan_session_pages SET position = -position WHERE session_id = ?",
            (session_id,),
        )

    def reorder(self, session_id: str, page_ids: list[str]) -> ScanSession:
        current = self.get(session_id)
        current_ids = [page.id for page in current.pages]
        if len(page_ids) != len(set(page_ids)) or set(page_ids) != set(current_ids):
            raise ValueError("Page order must contain every session page exactly once")
        with self.db.get_connection() as conn:
            for position, page_id in enumerate(page_ids, start=1):
                conn.execute(
                    "UPDATE scan_session_pages SET position = ? WHERE id = ? AND session_id = ?",
                    (-position, page_id, session_id),
                )
            conn.execute(
                "UPDATE scan_session_pages SET position = -position WHERE session_id = ?",
                (session_id,),
            )
            conn.execute(
                "UPDATE scan_sessions SET updated_at = ? WHERE id = ?",
                (self._now().isoformat(), session_id),
            )
        return self.get(session_id)

    def rotate(self, session_id: str, page_id: str) -> ScanSession:
        self._raw_session(session_id)
        path = self.page_path(session_id, page_id)
        with Image.open(path) as image:
            rotated = image.transpose(Image.Transpose.ROTATE_270)
            rotated.save(path, "JPEG", quality=92, optimize=True)
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE scan_sessions SET updated_at = ? WHERE id = ?",
                (self._now().isoformat(), session_id),
            )
        return self.get(session_id)

    def cancel(self, session_id: str) -> None:
        self._raw_session(session_id)
        registry = get_process_registry()
        if not registry.cancel(session_id):
            registry.finish(session_id)
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE scan_sessions SET status = 'cancelled', updated_at = ? WHERE id = ?",
                (self._now().isoformat(), session_id),
            )
            conn.execute("DELETE FROM scan_session_pages WHERE session_id = ?", (session_id,))
        shutil.rmtree(self._session_dir(session_id), ignore_errors=True)

    @staticmethod
    def _is_blank(image: Image.Image) -> bool:
        grayscale = image.convert("L").resize((64, 64))
        stats = ImageStat.Stat(grayscale)
        return stats.mean[0] > 248 and stats.stddev[0] < 4

    @staticmethod
    def _optimize_image(image: Image.Image) -> Image.Image:
        contrasted = ImageOps.autocontrast(image, cutoff=1)
        image.close()
        background = Image.new("RGB", contrasted.size, "white")
        difference = ImageChops.difference(contrasted, background).convert("L")
        bounds = difference.point(lambda value: 255 if value > 12 else 0).getbbox()
        if not bounds:
            return contrasted
        left, top, right, bottom = bounds
        padding = max(8, min(contrasted.size) // 100)
        crop = (
            max(0, left - padding),
            max(0, top - padding),
            min(contrasted.width, right + padding),
            min(contrasted.height, bottom + padding),
        )
        if crop == (0, 0, contrasted.width, contrasted.height):
            return contrasted
        cropped = contrasted.crop(crop)
        contrasted.close()
        return cropped

    def finalize(
        self,
        session_id: str,
        *,
        target_id: str,
        filename_prefix: str | None,
        optimize: bool,
        remove_blank_pages: bool,
        ocr: bool,
        pdfa: bool,
        ocr_language: str,
    ) -> FinalizeResult:
        session = self.get(session_id)
        if session.status != "active":
            raise ValueError(f"Scan session is {session.status}")
        if not session.pages:
            raise ValueError("Scan session has no pages")
        if pdfa and not ocr:
            raise ValueError("PDF/A requires OCR processing")

        job_id = str(uuid.uuid4())
        prefix = sanitize_filename_prefix(filename_prefix, "scan")
        output_dir = self.settings.data_dir / "scans"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{prefix}_{job_id}.pdf"
        raw_pdf = output_dir / f".{job_id}.raw.pdf"
        jobs = JobManager()
        jobs.create_job(
            job_id=job_id,
            job_type="scan",
            device_id=session.device_id,
            target_id=target_id,
            status=JobStatus.processing,
            max_retries=self.settings.delivery_max_retries,
            metadata={
                "session_id": session.id,
                "profile_id": session.profile_id,
                "pages": len(session.pages),
                "format": "pdf",
                "ocr": ocr,
                "pdfa": pdfa,
                "optimized": optimize,
            },
        )
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE scan_sessions SET status = 'processing', target_id = ?, updated_at = ? WHERE id = ?",
                (target_id, self._now().isoformat(), session_id),
            )

        images: list[Image.Image] = []
        try:
            profile = ScannerManager().resolve_profile(session.profile_id)
            for page in session.pages:
                with Image.open(self.page_path(session_id, page.id)) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    if optimize:
                        image = self._optimize_image(image)
                    if remove_blank_pages and self._is_blank(image):
                        image.close()
                        continue
                    images.append(image)
            if not images:
                raise ValueError("All captured pages were detected as blank")

            images[0].save(
                raw_pdf,
                "PDF",
                save_all=True,
                append_images=images[1:],
                resolution=float(profile.get("dpi", 200)),
                quality=int(profile.get("quality", 85)),
            )
            if ocr:
                command = [
                    "ocrmypdf",
                    "--deskew",
                    "--clean",
                    "--optimize",
                    "1",
                    "--language",
                    ocr_language,
                    "--output-type",
                    "pdfa-2" if pdfa else "pdf",
                    str(raw_pdf),
                    str(output_file),
                ]
                result = subprocess.run(command, capture_output=True, text=True, timeout=900)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "OCR processing failed")
                raw_pdf.unlink(missing_ok=True)
            else:
                raw_pdf.replace(output_file)

            job = jobs.get_job(job_id)
            if job:
                job.file_path = str(output_file)
                job.metadata["pages"] = len(images)
                jobs.update_job(job)
            get_delivery_retry_service().deliver_now(job_id)
            final_job = jobs.get_job(job_id)
            with self.db.get_connection() as conn:
                conn.execute(
                    "UPDATE scan_sessions SET status = 'completed', updated_at = ? WHERE id = ?",
                    (self._now().isoformat(), session_id),
                )
                conn.execute("DELETE FROM scan_session_pages WHERE session_id = ?", (session_id,))
            shutil.rmtree(self._session_dir(session_id), ignore_errors=True)
            return FinalizeResult(
                job_id=job_id,
                status=final_job.status if final_job else JobStatus.failed,
            )
        except Exception as exc:
            raw_pdf.unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)
            jobs.transition(job_id, JobStatus.failed, message=str(exc), last_error=str(exc))
            with self.db.get_connection() as conn:
                conn.execute(
                    "UPDATE scan_sessions SET status = 'active', updated_at = ? WHERE id = ?",
                    (self._now().isoformat(), session_id),
                )
            raise
        finally:
            for image in images:
                image.close()

    def cleanup_expired(self) -> int:
        cutoff = self._now() - timedelta(hours=self.settings.scan_session_ttl_hours)
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM scan_sessions WHERE status = 'active' AND updated_at < ?",
                (cutoff.isoformat(),),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE scan_sessions SET status = 'cancelled', updated_at = ? WHERE id = ?",
                    (self._now().isoformat(), row["id"]),
                )
                conn.execute("DELETE FROM scan_session_pages WHERE session_id = ?", (row["id"],))
        for row in rows:
            shutil.rmtree(self._session_dir(row["id"]), ignore_errors=True)
        return len(rows)

    def recover_interrupted(self) -> int:
        """Recover sessions left in processing state by an application restart."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT id FROM scan_sessions WHERE status = 'processing'"
            ).fetchall()
        jobs = JobManager()
        all_jobs = jobs.list_jobs(job_type="scan")
        recovered = 0
        for row in rows:
            session_id = row["id"]
            related = [job for job in all_jobs if job.metadata.get("session_id") == session_id]
            delivery_started = any(
                job.status
                in {
                    JobStatus.delivering,
                    JobStatus.retry_scheduled,
                    JobStatus.completed,
                    JobStatus.delivery_failed,
                }
                for job in related
            )
            new_status = "completed" if delivery_started else "active"
            if not delivery_started:
                for job in related:
                    if not job.status.terminal:
                        jobs.transition(
                            job.id,
                            JobStatus.failed,
                            message="Document processing interrupted by restart",
                            last_error="Document processing interrupted by restart",
                        )
                        if job.file_path:
                            Path(job.file_path).unlink(missing_ok=True)
            with self.db.get_connection() as conn:
                conn.execute(
                    "UPDATE scan_sessions SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status, self._now().isoformat(), session_id),
                )
                if delivery_started:
                    conn.execute(
                        "DELETE FROM scan_session_pages WHERE session_id = ?",
                        (session_id,),
                    )
            if delivery_started:
                shutil.rmtree(self._session_dir(session_id), ignore_errors=True)
            recovered += 1
        return recovered
