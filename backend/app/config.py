"""Application configuration.

Priority (highest → lowest):
  1. Environment variables   SCAN2TARGET_*
  2. Docker Secrets          /run/secrets/scan2target_*
  3. app_settings DB table   (editable via Web UI — runtime only)
  4. Hard-coded defaults
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRETS_DIR = "/run/secrets"
_secrets_dir_opt = _SECRETS_DIR if Path(_SECRETS_DIR).is_dir() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCAN2TARGET_",
        env_file=None,           # no .env file — use env vars or Docker Secrets
        secrets_dir=_secrets_dir_opt,
        case_sensitive=False,
        extra="ignore",
    )

    # ── Paths ─────────────────────────────────────────────────────────────
    database_path: str = "/data/db/scan2target.db"
    data_dir: Path = Path("/data")
    log_dir: str = "/var/log/scan2target"
    temp_dir: str = "/tmp/scan2target"

    # ── Security ──────────────────────────────────────────────────────────
    # JWT — auto-generated per process if not provided.
    jwt_secret: str | None = None
    jwt_expiration: int = 3600  # seconds

    # ── Runtime defaults (also stored/overridden in DB via Web UI) ────────
    require_auth: bool = False
    log_level: str = "INFO"
    health_check_interval: int = 60   # seconds
    scanner_check_interval: int = 30  # seconds
    command_timeout: int = 15         # seconds for subprocess calls
    cors_origins: list[str] = ["*"]

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid log_level {v!r}")
        return v

    def effective_jwt_secret(self) -> str:
        """Return JWT signing secret (generates one if not configured)."""
        return self.jwt_secret or secrets.token_urlsafe(32)


@lru_cache
def get_settings() -> Settings:
    """Singleton — cached after first call."""
    return Settings()
