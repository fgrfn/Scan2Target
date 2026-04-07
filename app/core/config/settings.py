"""Configuration loading with Docker Secrets and environment variable support.

Priority (highest to lowest):
  1. Environment variables  (SCAN2TARGET_*)
  2. Docker Secrets         (/run/secrets/scan2target_*)
  3. Hard-coded defaults

No .env file is used. In production, inject secrets via Docker Secrets
or directly as environment variables from your orchestrator (Compose,
Swarm, Kubernetes, systemd EnvironmentFile, …).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCAN2TARGET_",
        # No env_file — use proper env vars or Docker Secrets instead.
        env_file=None,
        # Docker Secrets are mounted under /run/secrets/ and named
        # scan2target_<field>  (e.g. /run/secrets/scan2target_secret_key).
        secrets_dir="/run/secrets",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "sqlite:////data/scan2target.db"
    database_path: str = "/data/scan2target.db"

    # ── Paths ─────────────────────────────────────────────────────────────
    data_dir: Path = Path("/data/scan2target")
    log_dir: str = "/var/log/scan2target"
    log_level: str = "INFO"
    temp_dir: str = "/tmp/scan2target/scans"

    # ── Scanner timing ────────────────────────────────────────────────────
    health_check_interval: int = 60   # seconds between scanner health checks
    scanner_check_interval: int = 30  # seconds between reachability polls
    command_timeout: int = 15         # max seconds for subprocess calls

    # ── Security ──────────────────────────────────────────────────────────
    # SCAN2TARGET_SECRET_KEY (or Docker Secret scan2target_secret_key)
    # Must be set in production. Auto-generated file-based key is used in
    # development as a fallback (see security.py).
    secret_key: str | None = None

    # JWT signing secret — auto-generated per process if not set.
    jwt_secret: str | None = None
    jwt_expiration: int = 3600  # token lifetime in seconds

    require_auth: bool = True
    allowed_subnets: list[str] = []

    # ── CORS ──────────────────────────────────────────────────────────────
    # Set to your frontend origin in production, e.g. ["https://scanner.home"]
    cors_origins: list[str] = ["*"]

    # ── Validators ────────────────────────────────────────────────────────
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        v = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid:
            raise ValueError(f"SCAN2TARGET_LOG_LEVEL must be one of {valid}, got {v!r}")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return the application settings singleton (cached after first call)."""
    return Settings()
