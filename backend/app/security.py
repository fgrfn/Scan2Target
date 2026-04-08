"""Fernet-based encryption for target credentials stored in the database."""
from __future__ import annotations

import base64
import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_SENSITIVE = frozenset({"password", "api_token", "access_token", "refresh_token"})


class SecureStorage:
    """Encrypts/decrypts sensitive fields in target config dicts."""

    def __init__(self) -> None:
        self._fernet = Fernet(self._resolve_key())

    # ── Key resolution ────────────────────────────────────────────────────

    def _resolve_key(self) -> bytes:
        from app.config import get_settings
        key_file = Path(get_settings().data_dir) / ".scan2target" / "encryption.key"
        if key_file.exists():
            return key_file.read_bytes()
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
        key_file.chmod(0o600)
        logger.info("Generated encryption key: %s", key_file)
        return key

    # ── Primitives ────────────────────────────────────────────────────────

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return base64.urlsafe_b64encode(self._fernet.encrypt(value.encode())).decode()

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._fernet.decrypt(base64.urlsafe_b64decode(value)).decode()
        except (InvalidToken, Exception) as exc:
            logger.error("Decryption failed: %s", exc)
            return ""

    # ── Config dict helpers ───────────────────────────────────────────────

    def encrypt_config(self, cfg: dict) -> dict:
        out = cfg.copy()
        for k in _SENSITIVE:
            if out.get(k):
                out[k] = self.encrypt(out[k])
        return out

    def decrypt_config(self, cfg: dict) -> dict:
        out = cfg.copy()
        for k in _SENSITIVE:
            if out.get(k):
                dec = self.decrypt(out[k])
                if dec:
                    out[k] = dec
        return out


_storage: SecureStorage | None = None


def get_storage() -> SecureStorage:
    global _storage
    if _storage is None:
        _storage = SecureStorage()
    return _storage
