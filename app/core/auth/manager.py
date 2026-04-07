"""Authentication utilities — JWT tokens and password hashing.

Password hashing  : passlib bcrypt (new hashes)
                    Legacy PBKDF2-SHA256 hashes are still verified and
                    automatically upgraded to bcrypt on next successful login.
JWT tokens        : python-jose (HS256)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.auth.models import User, UserRepository
from core.config.settings import get_settings
from core.database import get_db

logger = logging.getLogger(__name__)

# bcrypt is the primary scheme; legacy PBKDF2 hashes are deprecated but still
# accepted so existing users are not locked out after the upgrade.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_legacy_pbkdf2(password: str, password_hash: str) -> bool:
    """Verify a PBKDF2-SHA256 hash in the old 'salt_b64:hash_b64' format."""
    try:
        salt_b64, hash_b64 = password_hash.split(":", 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


class AuthManager:
    """JWT-based auth manager with bcrypt password hashing."""

    def __init__(self, secret_key: str | None = None):
        settings = get_settings()
        self.secret_key = secret_key or settings.jwt_secret or self._generate_secret()
        self.jwt_expiration = settings.jwt_expiration
        self.user_repo = UserRepository()
        self.db = get_db()

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _generate_secret() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _is_legacy_hash(password_hash: str) -> bool:
        """True if hash is in the old PBKDF2 'salt_b64:hash_b64' format."""
        return ":" in password_hash and not password_hash.startswith("$")

    # ── Password API ──────────────────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        """Return a bcrypt hash of *password*."""
        return _pwd_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify *password* against *password_hash* (bcrypt or legacy PBKDF2)."""
        if self._is_legacy_hash(password_hash):
            return _verify_legacy_pbkdf2(password, password_hash)
        return _pwd_context.verify(password, password_hash)

    # ── Token API ─────────────────────────────────────────────────────────

    def create_token(self, user: User, expires_in: int | None = None) -> str:
        """Create a signed JWT and persist it in the sessions table."""
        expiry = expires_in if expires_in is not None else self.jwt_expiration
        expire = datetime.now(timezone.utc) + timedelta(seconds=expiry)

        payload = {
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
            "exp": expire,
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        with self.db.get_connection() as conn:
            conn.cursor().execute(
                "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (token, user.id, expire.isoformat(), datetime.now(timezone.utc).isoformat()),
            )
        return token

    def verify_token(self, token: str) -> User | None:
        """Decode and validate a JWT; return the owner or None."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except JWTError as exc:
            logger.debug("Token decode failed: %s", exc)
            return None

        with self.db.get_connection() as conn:
            row = conn.cursor().execute(
                "SELECT revoked FROM sessions WHERE token = ?", (token,)
            ).fetchone()
        if not row or row["revoked"]:
            return None

        user = self.user_repo.get_by_id(int(payload["sub"]))
        if not user or not user.is_active:
            return None
        return user

    def revoke_token(self, token: str) -> bool:
        """Invalidate a token (logout)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET revoked = 1 WHERE token = ?", (token,))
                return cursor.rowcount > 0
        except Exception:
            return False

    # ── High-level auth ───────────────────────────────────────────────────

    def login(self, username: str, password: str) -> tuple[User, str] | None:
        """Authenticate a user; return (User, token) or None on failure.

        If the stored hash is the old PBKDF2 format it is transparently
        upgraded to bcrypt on a successful login.
        """
        result = self.user_repo.get_by_username(username)
        if not result:
            return None

        user, password_hash = result
        if not user.is_active:
            return None
        if not self.verify_password(password, password_hash):
            return None

        # Auto-upgrade legacy PBKDF2 hashes to bcrypt.
        if self._is_legacy_hash(password_hash):
            new_hash = self.hash_password(password)
            self.user_repo.update_password_hash(user.id, new_hash)
            logger.info("Upgraded password hash for %r to bcrypt", username)

        self.user_repo.update_last_login(user.id)
        return user, self.create_token(user)

    def register(
        self,
        username: str,
        password: str,
        email: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Create a new user; raises ValueError if username already exists."""
        if self.user_repo.user_exists(username):
            raise ValueError(f"Username {username!r} already exists")
        return self.user_repo.create(username, self.hash_password(password), email, is_admin)


# ── Singleton ─────────────────────────────────────────────────────────────────

_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Return the global AuthManager instance (created on first call)."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
