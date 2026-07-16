"""Authentication utilities for signed tokens and password hashing."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.auth.models import User, UserRepository
from core.config.settings import get_settings
from core.database import get_db

logger = logging.getLogger(__name__)
_PASSWORD_ITERATIONS = 310_000
_LEGACY_PASSWORD_ITERATIONS = 100_000
_PLACEHOLDER_SECRETS = {"changeme", "changeme-generate-a-secure-key", "your-secret-key"}


class AuthManager:
    """Authentication manager with persistent HMAC tokens and PBKDF2 hashes."""

    def __init__(self, secret_key: str | None = None):
        self.settings = get_settings()
        self.secret_key = secret_key or self._load_or_create_secret()
        self.user_repo = UserRepository()
        self.db = get_db()
        self.cleanup_expired_sessions()

    def _load_or_create_secret(self) -> str:
        """Load a stable JWT secret from config or a protected data file."""
        configured = self.settings.jwt_secret or os.getenv("SCAN2TARGET_SECRET_KEY")
        if configured and configured.strip().lower() not in _PLACEHOLDER_SECRETS:
            return configured.strip()
        if configured:
            logger.error("Ignoring insecure placeholder JWT secret")

        secret_file = Path(self.settings.data_dir) / "auth" / "jwt.secret"
        if secret_file.exists():
            secret = secret_file.read_text(encoding="utf-8").strip()
            if secret:
                return secret

        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_urlsafe(48)
        secret_file.write_text(secret, encoding="utf-8")
        secret_file.chmod(0o600)
        logger.warning("Generated persistent JWT secret at %s", secret_file)
        return secret

    def hash_password(self, password: str) -> str:
        """Hash a password using versioned PBKDF2-SHA256."""
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, _PASSWORD_ITERATIONS
        )
        return "$".join(
            (
                "pbkdf2_sha256",
                str(_PASSWORD_ITERATIONS),
                base64.b64encode(salt).decode(),
                base64.b64encode(digest).decode(),
            )
        )

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify current versioned hashes and legacy ``salt:hash`` values."""
        try:
            if password_hash.startswith("pbkdf2_sha256$"):
                _, iterations_raw, salt_b64, hash_b64 = password_hash.split("$", 3)
                iterations = int(iterations_raw)
            else:
                salt_b64, hash_b64 = password_hash.split(":", 1)
                iterations = _LEGACY_PASSWORD_ITERATIONS

            salt = base64.b64decode(salt_b64)
            expected_hash = base64.b64decode(hash_b64)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, iterations
            )
            return hmac.compare_digest(digest, expected_hash)
        except (ValueError, TypeError):
            return False

    def create_token(self, user: User, expires_in: int | None = None) -> str:
        """Create and persist a signed session token."""
        lifetime = expires_in or self.settings.jwt_expiration
        expires_at = datetime.utcnow() + timedelta(seconds=lifetime)
        payload = {
            "user_id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "exp": expires_at.timestamp(),
            "nonce": secrets.token_urlsafe(12),
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode()
        ).decode()
        signature = hmac.new(
            self.secret_key.encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()
        token = f"{payload_b64}.{signature}"

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, user.id, expires_at.isoformat(), datetime.utcnow().isoformat()),
            )
        return token

    def verify_token(self, token: str) -> Optional[User]:
        """Verify signature, expiry, session state and user state."""
        try:
            payload_b64, signature = token.split(".", 1)
            expected_sig = hmac.new(
                self.secret_key.encode(), payload_b64.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                return None

            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
            if datetime.utcnow().timestamp() > float(payload["exp"]):
                return None

            with self.db.get_connection() as conn:
                row = conn.execute(
                    "SELECT revoked, expires_at FROM sessions WHERE token = ?", (token,)
                ).fetchone()
                if not row or row["revoked"]:
                    return None
                if datetime.fromisoformat(row["expires_at"]) <= datetime.utcnow():
                    return None

            user = self.user_repo.get_by_id(int(payload["user_id"]))
            return user if user and user.is_active else None
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def revoke_token(self, token: str) -> bool:
        """Revoke a token during logout."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET revoked = 1 WHERE token = ?", (token,)
            )
            return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        """Remove expired session rows so the SQLite table cannot grow forever."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (datetime.utcnow().isoformat(),),
            )
            return cursor.rowcount

    def setup_required(self) -> bool:
        """Return whether the first administrator still needs to be created."""
        return self.user_repo.count_users() == 0

    def login(self, username: str, password: str) -> Optional[tuple[User, str]]:
        """Authenticate a user and return a new session token."""
        result = self.user_repo.get_by_username(username)
        if not result:
            return None
        user, password_hash = result
        if not user.is_active or not self.verify_password(password, password_hash):
            return None
        self.user_repo.update_last_login(user.id)
        return user, self.create_token(user)

    def register(
        self,
        username: str,
        password: str,
        email: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Register a user after route-level authorization and validation."""
        if self.user_repo.user_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        return self.user_repo.create(
            username, self.hash_password(password), email, is_admin
        )

    def update_account(
        self,
        user: User,
        current_password: str,
        username: str,
        email: str | None,
        new_password: str | None = None,
    ) -> tuple[User, str]:
        """Verify and update the operator account, rotating all sessions."""
        current = self.user_repo.get_by_username(user.username)
        if not current or not self.verify_password(current_password, current[1]):
            raise ValueError("Current password is incorrect")
        existing = self.user_repo.get_by_username(username)
        if existing and existing[0].id != user.id:
            raise ValueError(f"Username '{username}' already exists")
        updated = self.user_repo.update_account(
            int(user.id),
            username,
            email,
            self.hash_password(new_password) if new_password else None,
        )
        with self.db.get_connection() as conn:
            conn.execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user.id,))
        return updated, self.create_token(updated)


_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Get or create the process-wide authentication manager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
