"""HTTP based delivery target adapters."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

import requests

from core.targets.adapters.base import DeliveryAdapter
from core.targets.models import NextcloudConfig, PaperlessConfig, TargetConfig, WebhookConfig
from core.validation import validate_webhook_url


class PaperlessAdapter(DeliveryAdapter):
    config_model = PaperlessConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        result["url"] = result.get("url") or result.get("connection")
        result["api_token"] = result.get("api_token") or result.get("token")
        tags = result.get("tags") or []
        if isinstance(tags, str):
            result["tags"] = [int(value.strip()) for value in tags.split(",") if value.strip().isdigit()]
        return result

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            response = requests.get(
                f"{config.url.rstrip('/')}/api/",
                headers={"Authorization": f"Token {config.api_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"status": "ok", "message": "Paperless-ngx connected"}
            return {"status": "error", "message": f"Paperless returned HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        mime_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        data: dict[str, Any] = {"title": metadata.get("title") or file.stem}
        if config.correspondent is not None:
            data["correspondent"] = str(config.correspondent)
        if config.document_type is not None:
            data["document_type"] = str(config.document_type)
        if config.tags:
            data["tags"] = [str(tag) for tag in config.tags]
        with file.open("rb") as stream:
            response = requests.post(
                f"{config.url.rstrip('/')}/api/documents/post_document/",
                headers={"Authorization": f"Token {config.api_token}"},
                files={"document": (file.name, stream, mime_type)},
                data=data,
                timeout=60,
            )
        response.raise_for_status()


class WebhookAdapter(DeliveryAdapter):
    config_model = WebhookConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        result["url"] = result.get("url") or result.get("connection")
        return result

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            url = validate_webhook_url(config.url)
            response = requests.head(url, timeout=10, allow_redirects=False)
            if response.status_code < 500:
                return {"status": "ok", "message": f"Webhook reachable (HTTP {response.status_code})"}
            return {"status": "error", "message": f"Webhook returned HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        url = validate_webhook_url(config.url)
        with file.open("rb") as stream:
            response = requests.post(
                url,
                files={"file": (file.name, stream)},
                data={key: str(value) for key, value in metadata.items()},
                timeout=60,
                allow_redirects=False,
            )
        response.raise_for_status()


class NextcloudAdapter(DeliveryAdapter):
    config_model = NextcloudConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        result["url"] = result.get("url") or result.get("connection") or result.get("webdav_url")
        return result

    @staticmethod
    def _dav_url(config: NextcloudConfig, filename: str = "") -> str:
        base = config.url.rstrip("/")
        path = config.path.strip("/")
        suffix = f"/{path}" if path else ""
        if filename:
            suffix += f"/{filename}"
        return f"{base}/remote.php/dav/files/{config.username}{suffix}"

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            response = requests.request(
                "PROPFIND",
                self._dav_url(config),
                auth=(config.username, config.password),
                headers={"Depth": "0"},
                timeout=10,
            )
            if response.status_code in {200, 207, 301, 302, 404}:
                return {"status": "ok", "message": "Nextcloud WebDAV connected"}
            return {"status": "error", "message": f"Nextcloud returned HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        with file.open("rb") as stream:
            response = requests.put(
                self._dav_url(config, file.name),
                auth=(config.username, config.password),
                data=stream,
                timeout=60,
            )
        response.raise_for_status()
