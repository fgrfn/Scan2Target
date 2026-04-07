"""DB-backed runtime settings — editable via Web UI without restart."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.database import get_db

logger = logging.getLogger(__name__)

# Keys that are allowed to be stored and edited via the Web UI.
EDITABLE_KEYS = {
    "require_auth",
    "log_level",
    "health_check_interval",
    "scanner_check_interval",
    "command_timeout",
    "cors_origins",
}


def get_all() -> dict[str, Any]:
    with get_db().connection() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {r["key"]: json.loads(r["value"]) for r in rows}


def get_setting(key: str, default: Any = None) -> Any:
    with get_db().connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    if row:
        return json.loads(row["value"])
    # Fall back to static config
    from app.config import get_settings
    return getattr(get_settings(), key, default)


def set_setting(key: str, value: Any) -> None:
    if key not in EDITABLE_KEYS:
        raise ValueError(f"Setting {key!r} is not editable via the Web UI")
    raw = json.dumps(value)
    with get_db().connection() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%S','now')",
            (key, raw),
        )
    logger.info("Setting %r updated to %r", key, value)
