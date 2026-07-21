"""Configuration loading and security-sensitive defaults."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from ``SCAN2TARGET_*`` environment variables."""

    # Database
    database_url: str = "sqlite:////data/db/scan2target.db"
    database_path: str = "/data/db/scan2target.db"

    # Paths
    data_dir: Path = Path("/data")
    secret_key_path: Path = Path("/data/auth/encryption.key")

    # Security
    allowed_subnets: list[str] = []
    require_auth: bool = True
    jwt_secret: Optional[str] = None
    jwt_expiration: int = 3600
    cors_origins: str = ""
    allow_private_webhooks: bool = False

    # Request limits
    max_request_size_mb: int = 100
    max_batch_page_mb: int = 20
    max_batch_pages: int = 100
    scan_session_ttl_hours: int = 24

    # Persistent delivery retry queue
    retry_poll_interval: int = 15
    retry_base_delay: int = 30
    retry_max_delay: int = 3600
    delivery_max_retries: int = 5

    # Home Assistant integration
    ha_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="SCAN2TARGET_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return explicitly configured browser origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the process-wide settings instance."""
    return Settings()
