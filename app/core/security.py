"""Security utilities for encrypting sensitive target configuration data."""
from __future__ import annotations

import base64
import logging
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Salt used when deriving the Fernet key from SCAN2TARGET_SECRET_KEY.
# Changing this will invalidate all previously encrypted target credentials.
_KDF_SALT = b"scan2target_v1"
_KDF_ITERATIONS = 100_000


class SecureStorage:
    """Encrypts and decrypts sensitive configuration fields (passwords, tokens)."""

    def __init__(self) -> None:
        self.key = self._resolve_key()
        self.cipher = Fernet(self.key)

    # ── Key resolution (priority: env/settings → file fallback) ──────────

    def _resolve_key(self) -> bytes:
        """Derive the Fernet key.

        1. ``SCAN2TARGET_SECRET_KEY`` environment variable / Docker Secret
           → key is derived with PBKDF2-SHA256 so it can be any string.
        2. File-based auto-generated key in ``~/.scan2target/encryption.key``
           (development fallback only — never use this in production).
        """
        from core.config.settings import get_settings
        raw_secret = get_settings().secret_key

        if raw_secret:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=_KDF_SALT,
                iterations=_KDF_ITERATIONS,
            )
            return base64.urlsafe_b64encode(kdf.derive(raw_secret.encode()))

        # Development fallback — auto-generate and persist a key file.
        key_file = Path.home() / ".scan2target" / "encryption.key"
        if key_file.exists():
            return key_file.read_bytes()

        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
        key_file.chmod(0o600)

        logger.warning("[SECURITY] Generated new encryption key: %s", key_file)
        logger.warning(
            "[SECURITY] Set SCAN2TARGET_SECRET_KEY (env var or Docker Secret) in production."
        )
        return key

    # ── Encrypt / decrypt primitives ──────────────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* and return a URL-safe base64 string."""
        if not plaintext:
            return ""
        return base64.urlsafe_b64encode(self.cipher.encrypt(plaintext.encode())).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt *ciphertext*; returns ``""`` if decryption fails."""
        if not ciphertext:
            return ""
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            return self.cipher.decrypt(decoded).decode()
        except Exception as exc:
            logger.error("[SECURITY] Decryption failed: %s", exc)
            return ""

    # ── Config dict helpers ───────────────────────────────────────────────

    _SENSITIVE_FIELDS = frozenset({"password", "api_token", "access_token", "refresh_token"})

    def encrypt_config(self, config: dict) -> dict:
        """Return *config* with sensitive fields encrypted."""
        out = config.copy()
        for field in self._SENSITIVE_FIELDS:
            if out.get(field):
                out[field] = self.encrypt(out[field])
        return out

    def decrypt_config(self, config: dict) -> dict:
        """Return *config* with sensitive fields decrypted."""
        out = config.copy()
        for field in self._SENSITIVE_FIELDS:
            if out.get(field):
                decrypted = self.decrypt(out[field])
                if decrypted:
                    out[field] = decrypted
        return out


# ── Singleton ─────────────────────────────────────────────────────────────────

_secure_storage: SecureStorage | None = None


def get_secure_storage() -> SecureStorage:
    """Return the global SecureStorage instance (created on first call)."""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage
