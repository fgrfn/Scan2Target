"""SQLite connection management + Alembic migration runner."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class Database:
    """Thread-safe SQLite connection factory with row-dict access."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def run_migrations(db_path: str) -> None:
    """Run Alembic migrations to bring the schema up to date."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(Path(__file__).parent.parent / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


# ── Singleton ─────────────────────────────────────────────────────────────────

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        from app.config import get_settings
        _db = Database(get_settings().database_path)
    return _db
