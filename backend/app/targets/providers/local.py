from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseProvider


class LocalFolderProvider(BaseProvider):
    """Deliver scanned files to a local directory on the server / container."""

    def test(self, config: dict) -> None:
        path = Path(config["path"])
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise ConnectionError(f"Cannot create folder '{path}': {exc}") from exc
        if not os.access(path, os.W_OK):
            raise ConnectionError(f"Folder '{path}' exists but is not writable")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        dest_dir = Path(config["path"])
        if config.get("subfolder_per_day"):
            dest_dir = dest_dir / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest_dir / filename)
