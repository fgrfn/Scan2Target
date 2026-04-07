from __future__ import annotations
from pathlib import Path
import requests
from .base import BaseProvider


class PaperlessProvider(BaseProvider):
    def _headers(self, config: dict) -> dict:
        return {"Authorization": f"Token {config['api_token']}"}

    def test(self, config: dict) -> None:
        url = config["connection"].rstrip("/")
        r = requests.get(f"{url}/api/", headers=self._headers(config), timeout=10)
        if r.status_code not in (200, 301, 302):
            raise ConnectionError(f"Paperless returned {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        url = config["connection"].rstrip("/")
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{url}/api/documents/post_document/",
                headers=self._headers(config),
                files={"document": (filename, f)},
                timeout=120,
            )
        if r.status_code not in (200, 201, 202):
            raise RuntimeError(f"Paperless upload failed: {r.status_code} {r.text[:200]}")
