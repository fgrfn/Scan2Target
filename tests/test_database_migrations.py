"""Database migration, backup and integrity tests."""
from __future__ import annotations

import sqlite3

from core.database import Database


def test_legacy_database_is_backed_up_and_migrated(tmp_path):
    path = tmp_path / "scan2target.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            device_id TEXT,
            target_id TEXT,
            printer_id TEXT,
            status TEXT NOT NULL,
            file_path TEXT,
            message TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO jobs VALUES ('legacy', 'scan', NULL, NULL, NULL, 'completed', NULL, NULL, '2026-01-01', '2026-01-01')"
    )
    conn.commit()
    conn.close()

    database = Database(str(path))

    with database.get_connection() as migrated:
        version = migrated.execute("PRAGMA user_version").fetchone()[0]
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(jobs)")}
        legacy = migrated.execute("SELECT id, status FROM jobs WHERE id = 'legacy'").fetchone()

    assert version == Database.LATEST_SCHEMA_VERSION
    assert {"thumbnail_path", "retry_count", "next_retry_at", "metadata_json"} <= columns
    assert tuple(legacy) == ("legacy", "completed")
    assert database.list_backups()
    assert database.integrity_check()["ok"] is True


def test_manual_backup_and_restore(tmp_path):
    database = Database(str(tmp_path / "scan2target.db"))
    with database.get_connection() as conn:
        conn.execute(
            "INSERT INTO jobs(id, job_type, status, created_at, updated_at) VALUES ('one', 'scan', 'completed', '2026-01-01', '2026-01-01')"
        )
    backup = database.create_backup("test")
    with database.get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE id = 'one'")
    database.restore_backup(backup.name)
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM jobs WHERE id = 'one'").fetchone()[0] == 1
