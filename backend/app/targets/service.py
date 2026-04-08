"""Target CRUD, validation, delivery."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.database import get_db
from app.security import get_storage
from app.targets.providers.base import BaseProvider
from app.targets.providers.smb import SMBProvider
from app.targets.providers.sftp import SFTPProvider
from app.targets.providers.email import EmailProvider
from app.targets.providers.paperless import PaperlessProvider
from app.targets.providers.webhook import WebhookProvider
from app.targets.providers.cloud import (
    GoogleDriveProvider, DropboxProvider, OneDriveProvider, NextcloudProvider
)

PROVIDERS: dict[str, type[BaseProvider]] = {
    "smb":          SMBProvider,
    "sftp":         SFTPProvider,
    "email":        EmailProvider,
    "paperless":    PaperlessProvider,
    "webhook":      WebhookProvider,
    "google_drive": GoogleDriveProvider,
    "dropbox":      DropboxProvider,
    "onedrive":     OneDriveProvider,
    "nextcloud":    NextcloudProvider,
}

_MASK = frozenset({"password", "api_token", "access_token", "refresh_token"})


def _mask(cfg: dict) -> dict:
    return {k: ("***" if k in _MASK and v else v) for k, v in cfg.items()}


def _row(r: Any) -> dict:
    d = dict(r)
    d["config"] = _mask(json.loads(d["config"]))
    return d


def list_targets() -> list[dict]:
    with get_db().connection() as conn:
        rows = conn.execute("SELECT * FROM targets WHERE enabled=1 ORDER BY is_favorite DESC, name").fetchall()
    return [_row(r) for r in rows]


def get_target(target_id: str) -> dict | None:
    with get_db().connection() as conn:
        r = conn.execute("SELECT * FROM targets WHERE id=?", (target_id,)).fetchone()
    return _row(r) if r else None


def _raw_config(target_id: str) -> dict:
    with get_db().connection() as conn:
        r = conn.execute("SELECT config FROM targets WHERE id=?", (target_id,)).fetchone()
    return get_storage().decrypt_config(json.loads(r["config"])) if r else {}


def create_target(data: dict) -> dict:
    target_id = str(uuid.uuid4())[:8]
    enc = get_storage().encrypt_config(data["config"])
    with get_db().connection() as conn:
        conn.execute(
            "INSERT INTO targets (id, type, name, config, enabled, description, is_favorite) "
            "VALUES (?,?,?,?,?,?,?)",
            (target_id, data["type"].lower(), data["name"], json.dumps(enc),
             1 if data.get("enabled", True) else 0,
             data.get("description"), 1 if data.get("is_favorite") else 0),
        )
    return get_target(target_id)


def update_target(target_id: str, data: dict) -> dict | None:
    enc = get_storage().encrypt_config(data["config"])
    with get_db().connection() as conn:
        conn.execute(
            "UPDATE targets SET type=?, name=?, config=?, enabled=?, description=?, is_favorite=?, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%S','now') WHERE id=?",
            (data["type"].lower(), data["name"], json.dumps(enc),
             1 if data.get("enabled", True) else 0,
             data.get("description"), 1 if data.get("is_favorite") else 0, target_id),
        )
    return get_target(target_id)


def delete_target(target_id: str) -> bool:
    with get_db().connection() as conn:
        cur = conn.execute("DELETE FROM targets WHERE id=?", (target_id,))
    return cur.rowcount > 0


def set_favorite(target_id: str, is_favorite: bool) -> dict | None:
    with get_db().connection() as conn:
        conn.execute("UPDATE targets SET is_favorite=? WHERE id=?", (1 if is_favorite else 0, target_id))
    return get_target(target_id)


def test_target(target_id: str) -> None:
    """Test connectivity. Raises on failure."""
    tgt = get_target(target_id)
    if not tgt:
        raise ValueError(f"Target {target_id!r} not found")
    cfg = _raw_config(target_id)
    provider = PROVIDERS.get(tgt["type"].lower())
    if not provider:
        raise ValueError(f"Unknown target type: {tgt['type']!r}")
    provider().test(cfg)


def test_config(target_type: str, config: dict) -> None:
    """Test a config dict before saving."""
    provider = PROVIDERS.get(target_type.lower())
    if not provider:
        raise ValueError(f"Unknown target type: {target_type!r}")
    provider().test(config)


def deliver(target_id: str, file_path: Path, filename: str) -> None:
    """Deliver a file to a target. Raises on failure."""
    tgt = get_target(target_id)
    if not tgt:
        raise ValueError(f"Target {target_id!r} not found")
    cfg = _raw_config(target_id)
    provider = PROVIDERS.get(tgt["type"].lower())
    if not provider:
        raise ValueError(f"Unknown target type: {tgt['type']!r}")
    provider().deliver(cfg, file_path, filename)


def get_favorite_target() -> dict | None:
    with get_db().connection() as conn:
        r = conn.execute("SELECT * FROM targets WHERE is_favorite=1 AND enabled=1 LIMIT 1").fetchone()
    return _row(r) if r else None
