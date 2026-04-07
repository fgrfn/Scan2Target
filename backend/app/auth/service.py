"""JWT + bcrypt authentication service.

Legacy PBKDF2 hashes (salt_b64:hash_b64) are verified and auto-upgraded
to bcrypt on the next successful login — no user lockout after upgrade.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import get_db

logger = logging.getLogger(__name__)
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _pwd.hash(password)


def _is_legacy(h: str) -> bool:
    return ":" in h and not h.startswith("$")


def _verify_legacy(password: str, h: str) -> bool:
    try:
        salt_b64, hash_b64 = h.split(":", 1)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                        base64.b64decode(salt_b64), 100_000)
        return hmac.compare_digest(computed, base64.b64decode(hash_b64))
    except Exception:
        return False


def verify_password(password: str, stored_hash: str) -> bool:
    if _is_legacy(stored_hash):
        return _verify_legacy(password, stored_hash)
    return _pwd.verify(password, stored_hash)


# ── User DB helpers ───────────────────────────────────────────────────────────

def _row_to_user(row: Any) -> dict:
    return {
        "id": row["id"], "username": row["username"], "email": row["email"],
        "is_active": bool(row["is_active"]), "is_admin": bool(row["is_admin"]),
        "created_at": row["created_at"], "last_login": row["last_login"],
    }


def get_user_by_username(username: str) -> tuple[dict, str] | None:
    with get_db().connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if row:
        return _row_to_user(row), row["password_hash"]
    return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db().connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def create_user(username: str, password: str, email: str | None, is_admin: bool) -> dict:
    with get_db().connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, email, is_admin) VALUES (?,?,?,?)",
            (username, hash_password(password), email, 1 if is_admin else 0),
        )
        return get_user_by_id(cur.lastrowid)


def user_exists(username: str) -> bool:
    with get_db().connection() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
    return row is not None


def update_password_hash(user_id: int, new_hash: str) -> None:
    with get_db().connection() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))


def update_last_login(user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db().connection() as conn:
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now, user_id))


# ── JWT helpers ───────────────────────────────────────────────────────────────

_jwt_secret: str | None = None


def _secret() -> str:
    global _jwt_secret
    if _jwt_secret is None:
        from app.config import get_settings
        s = get_settings()
        _jwt_secret = s.jwt_secret or secrets.token_urlsafe(32)
    return _jwt_secret


def create_token(user: dict, expiry_seconds: int | None = None) -> str:
    from app.config import get_settings
    exp = expiry_seconds or get_settings().jwt_expiration
    expire = datetime.now(timezone.utc) + timedelta(seconds=exp)
    payload = {"sub": str(user["id"]), "username": user["username"],
               "is_admin": user["is_admin"], "exp": expire}
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    with get_db().connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
            (token, user["id"], expire.isoformat()),
        )
    return token


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    except JWTError:
        return None
    with get_db().connection() as conn:
        row = conn.execute("SELECT revoked FROM sessions WHERE token=?", (token,)).fetchone()
    if not row or row["revoked"]:
        return None
    return get_user_by_id(int(payload["sub"]))


def revoke_token(token: str) -> bool:
    with get_db().connection() as conn:
        cur = conn.execute("UPDATE sessions SET revoked=1 WHERE token=?", (token,))
    return cur.rowcount > 0


# ── High-level login ──────────────────────────────────────────────────────────

def login(username: str, password: str) -> tuple[dict, str] | None:
    result = get_user_by_username(username)
    if not result:
        return None
    user, stored_hash = result
    if not user["is_active"] or not verify_password(password, stored_hash):
        return None
    # Auto-upgrade legacy PBKDF2 → bcrypt
    if _is_legacy(stored_hash):
        update_password_hash(user["id"], hash_password(password))
        logger.info("Upgraded password hash for %r to bcrypt", username)
    update_last_login(user["id"])
    return user, create_token(user)


def init_admin() -> None:
    """Create the default admin user if no users exist."""
    if not user_exists("admin"):
        create_user("admin", "admin", "admin@scan2target.local", is_admin=True)
        logger.warning("Default admin created — username: admin / password: admin — CHANGE IMMEDIATELY!")
