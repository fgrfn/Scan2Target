"""Device (scanner) persistence layer."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.database import get_db


def _row(r: Any) -> dict:
    return dict(r)


def _sanitize_id(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())[:64]


def list_devices(device_type: str | None = None) -> list[dict]:
    q = "SELECT * FROM devices WHERE is_active=1"
    params: list = []
    if device_type:
        q += " AND device_type=?"
        params.append(device_type)
    q += " ORDER BY is_favorite DESC, name"
    with get_db().connection() as conn:
        return [_row(r) for r in conn.execute(q, params).fetchall()]


def get_device(device_id: str) -> dict | None:
    with get_db().connection() as conn:
        r = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
    return _row(r) if r else None


def get_device_by_uri(uri: str) -> dict | None:
    with get_db().connection() as conn:
        r = conn.execute("SELECT * FROM devices WHERE uri=?", (uri,)).fetchone()
    return _row(r) if r else None


def add_device(req: dict) -> dict:
    device_id = _sanitize_id(req.get("name", req["uri"]))
    # Ensure uniqueness
    base, i = device_id, 1
    with get_db().connection() as conn:
        while conn.execute("SELECT 1 FROM devices WHERE id=?", (device_id,)).fetchone():
            device_id = f"{base}_{i}"; i += 1
        conn.execute(
            "INSERT INTO devices (id, device_type, name, uri, make, model, connection_type, description) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (device_id, req.get("device_type", "scanner"), req["name"], req["uri"],
             req.get("make"), req.get("model"), req.get("connection_type"), req.get("description")),
        )
    return get_device(device_id)


def remove_device(device_id: str) -> bool:
    with get_db().connection() as conn:
        cur = conn.execute("UPDATE devices SET is_active=0 WHERE id=?", (device_id,))
    return cur.rowcount > 0


def set_favorite(device_id: str, is_favorite: bool) -> dict | None:
    with get_db().connection() as conn:
        conn.execute("UPDATE devices SET is_favorite=? WHERE id=?", (1 if is_favorite else 0, device_id))
    return get_device(device_id)


def touch_last_seen(device_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db().connection() as conn:
        conn.execute("UPDATE devices SET last_seen=? WHERE id=?", (now, device_id))


def get_all_uris() -> list[str]:
    with get_db().connection() as conn:
        return [r[0] for r in conn.execute("SELECT uri FROM devices WHERE is_active=1").fetchall()]
