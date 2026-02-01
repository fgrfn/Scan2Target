"""Configuration loading and secrets handling."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:////app/scan2target.db"
    database_path: str = "/app/scan2target.db"
    
    # Paths
    data_dir: Path = Path("/data/scan2target")
    secret_key_path: Path = Path("/etc/scan2target/secret.key")
    
    # Security
    allowed_subnets: list[str] = []
    require_auth: bool = False  # Set to True to require authentication
    jwt_secret: Optional[str] = None  # Auto-generated if not set
    jwt_expiration: int = 3600  # Token expiration in seconds (1 hour)
    
    # CORS
    cors_origins: list[str] = ["*"]  # Tighten in production

    class Config:
        env_prefix = "SCAN2TARGET_"
        env_file = ".env"


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
