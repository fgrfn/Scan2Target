from __future__ import annotations
from pathlib import Path
import requests
from .base import BaseProvider


class WebhookProvider(BaseProvider):
    def test(self, config: dict) -> None:
        r = requests.head(config["connection"], timeout=10)
        if r.status_code >= 500:
            raise ConnectionError(f"Webhook endpoint returned {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        with open(file_path, "rb") as f:
            r = requests.post(config["connection"],
                              files={"file": (filename, f)}, timeout=120)
        if not r.ok:
            raise RuntimeError(f"Webhook delivery failed: {r.status_code} {r.text[:200]}")
