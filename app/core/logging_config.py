"""Centralized logging configuration for Scan2Target."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Configure application-wide logging.

    Log level and directory are read from Settings so they can be controlled
    via the SCAN2TARGET_LOG_LEVEL and SCAN2TARGET_LOG_DIR environment variables
    (or Docker Secrets) without touching any file.

    Logs to:
    - Console (stdout)
    - File: <log_dir>/app.log  (rotated at 10 MB, 5 backups)
    """
    # Import here to avoid a circular import at module load time.
    from core.config.settings import get_settings
    settings = get_settings()

    log_level = getattr(logging, settings.log_level, logging.INFO)
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # always verbose in the file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.info("Logging initialised — file: %s  level: %s", log_file, settings.log_level)
    except OSError as exc:
        logging.warning("Could not set up file logging: %s", exc)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
