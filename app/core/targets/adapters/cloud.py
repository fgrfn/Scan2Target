"""Cloud storage delivery adapters."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import requests

from core.targets.adapters.base import DeliveryAdapter
from core.targets.cloud import DropboxHandler, GoogleDriveHandler, OneDriveHandler
from core.targets.models import CloudTokenConfig, TargetConfig


class CloudAdapter(DeliveryAdapter):
    config_model = CloudTokenConfig
    upload_handler: Callable[[Path, dict], None]
    validation_url: str

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            response = requests.get(
                self.validation_url,
                headers={"Authorization": f"Bearer {config.access_token}"},
                timeout=10,
            )
            if response.status_code < 400:
                return {"status": "ok", "message": "Cloud credentials valid"}
            return {"status": "error", "message": f"Cloud API returned HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        self.upload_handler(file, config.model_dump(exclude_none=True))


class GoogleDriveAdapter(CloudAdapter):
    upload_handler = staticmethod(GoogleDriveHandler.upload)
    validation_url = "https://www.googleapis.com/drive/v3/about?fields=user"


class DropboxAdapter(CloudAdapter):
    upload_handler = staticmethod(DropboxHandler.upload)
    validation_url = "https://api.dropboxapi.com/2/users/get_current_account"

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            response = requests.post(
                self.validation_url,
                headers={"Authorization": f"Bearer {config.access_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"status": "ok", "message": "Dropbox credentials valid"}
            return {"status": "error", "message": f"Dropbox returned HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


class OneDriveAdapter(CloudAdapter):
    upload_handler = staticmethod(OneDriveHandler.upload)
    validation_url = "https://graph.microsoft.com/v1.0/me/drive"
