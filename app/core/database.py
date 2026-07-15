"""SQLite database setup, migrations, backups and integrity helpers."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Generator


Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


class Database:
    """SQLite connection manager with transactional schema migrations."""

    LATEST_SCHEMA_VERSION = 3

    def __init__(self, db_path: str = "scan2target.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a configured connection with automatic commit and rollback."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _schema_version(self) -> int:
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            return 0
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])
        finally:
            conn.close()

    def _migrate(self) -> None:
        current = self._schema_version()
        migrations: list[Migration] = [
            (1, "baseline schema", self._migration_baseline),
            (2, "persistent delivery retries", self._migration_delivery_retries),
            (3, "delivery attempt audit log", self._migration_delivery_attempts),
        ]
        pending = [migration for migration in migrations if migration[0] > current]
        if not pending:
            return

        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            self.create_backup(label=f"pre-schema-v{pending[-1][0]}")

        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            for version, name, migration in pending:
                migration(conn)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                    (version, name, datetime.now(timezone.utc).isoformat()),
                )
                conn.execute(f"PRAGMA user_version = {version}")

    @staticmethod
    def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    @classmethod
    def _add_column(cls, conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
        if name not in cls._columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _migration_baseline(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                device_id TEXT,
                target_id TEXT,
                printer_id TEXT,
                status TEXT NOT NULL,
                file_path TEXT,
                thumbnail_path TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS targets (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                config TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                description TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scan_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dpi INTEGER NOT NULL,
                color_mode TEXT NOT NULL,
                paper_size TEXT NOT NULL,
                format TEXT NOT NULL,
                quality INTEGER DEFAULT 85,
                source TEXT DEFAULT 'Flatbed',
                batch_scan INTEGER DEFAULT 0,
                auto_detect INTEGER DEFAULT 1,
                description TEXT DEFAULT '',
                is_builtin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                name TEXT NOT NULL,
                uri TEXT NOT NULL UNIQUE,
                make TEXT,
                model TEXT,
                connection_type TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                is_favorite INTEGER DEFAULT 0,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_type_created ON jobs(job_type, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
            CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
            CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active);
            """
        )
        for column, definition in {
            "quality": "INTEGER DEFAULT 85",
            "source": "TEXT DEFAULT 'Flatbed'",
            "batch_scan": "INTEGER DEFAULT 0",
            "auto_detect": "INTEGER DEFAULT 1",
            "description": "TEXT DEFAULT ''",
            "is_builtin": "INTEGER DEFAULT 0",
        }.items():
            self._add_column(conn, "scan_profiles", column, definition)
        self._add_column(conn, "jobs", "thumbnail_path", "TEXT")

    def _migration_delivery_retries(self, conn: sqlite3.Connection) -> None:
        for column, definition in {
            "retry_count": "INTEGER NOT NULL DEFAULT 0",
            "max_retries": "INTEGER NOT NULL DEFAULT 5",
            "next_retry_at": "TEXT",
            "last_error": "TEXT",
            "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            "delivery_started_at": "TEXT",
            "completed_at": "TEXT",
        }.items():
            self._add_column(conn, "jobs", column, definition)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_retry_due ON jobs(status, next_retry_at)"
        )

    def _migration_delivery_attempts(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS delivery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_delivery_attempts_job ON delivery_attempts(job_id, attempt);
            """
        )

    def create_backup(self, label: str = "manual") -> Path:
        """Create a consistent SQLite backup and return its path."""
        safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label)[:40]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.backup_dir / f"scan2target-{timestamp}-{safe_label}.db"
        source = sqlite3.connect(self.db_path, timeout=30)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination

    def list_backups(self) -> list[dict]:
        return [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            }
            for path in sorted(self.backup_dir.glob("*.db"), reverse=True)
        ]

    def restore_backup(self, name: str) -> Path:
        """Restore a named backup after validating it and preserving the current DB."""
        source = (self.backup_dir / Path(name).name).resolve()
        if source.parent != self.backup_dir.resolve() or not source.exists():
            raise FileNotFoundError("Backup not found")
        check = sqlite3.connect(source)
        try:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if result != "ok":
            raise ValueError(f"Backup integrity check failed: {result}")
        self.create_backup(label="pre-restore")
        temporary = self.db_path.with_suffix(".restore.tmp")
        shutil.copy2(source, temporary)
        temporary.replace(self.db_path)
        return self.db_path

    def integrity_check(self) -> dict:
        with self.get_connection() as conn:
            rows = [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]
            foreign_keys = [dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
        return {"ok": rows == ["ok"] and not foreign_keys, "integrity": rows, "foreign_keys": foreign_keys}

    def export_json(self) -> Path:
        """Export non-secret application data for diagnostics and migration."""
        tables = ["jobs", "delivery_attempts", "devices", "scan_profiles"]
        payload: dict[str, list[dict]] = {}
        with self.get_connection() as conn:
            for table in tables:
                payload[table] = [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.backup_dir / f"scan2target-export-{timestamp}.json"
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return destination


_db_instance: Database | None = None


def get_db() -> Database:
    """Get or create the process-wide database instance."""
    global _db_instance
    if _db_instance is None:
        db_path = os.getenv("SCAN2TARGET_DATABASE_PATH") or os.getenv(
            "SCAN2TARGET_DB_PATH", "scan2target.db"
        )
        _db_instance = Database(db_path)
    return _db_instance
