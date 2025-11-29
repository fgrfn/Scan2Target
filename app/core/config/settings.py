"""Configuration loading and secrets handling stubs."""
from __future__ import annotations
from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./raspscan.db"
    data_dir: Path = Path("/data/raspscan")
    secret_key_path: Path = Path("/etc/raspscan/secret.key")
    allowed_subnets: list[str] = []

    class Config:
        env_prefix = "RASPSCAN_"
        env_file = ".env"
