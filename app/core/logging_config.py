"""Centralized logging configuration for Scan2Target."""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os


def setup_logging():
    """
    Configure application-wide logging.
    
    Logs to:
    - Console (stdout/stderr)
    - File: /var/log/scan2target/app.log (rotated at 10MB, 5 backups)
    """
    # Create log directory
    log_dir = Path(os.getenv('SCAN2TARGET_LOG_DIR', '/var/log/scan2target'))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'app.log'
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Format for logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # More detailed in file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"Logging initialized - file: {log_file}")
    except Exception as e:
        logging.warning(f"Could not set up file logging: {e}")
    
    return root_logger


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)
