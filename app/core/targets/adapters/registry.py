"""Target adapter registry."""
from __future__ import annotations

from core.targets.adapters.base import DeliveryAdapter
from core.targets.adapters.cloud import DropboxAdapter, GoogleDriveAdapter, OneDriveAdapter
from core.targets.adapters.http import NextcloudAdapter, PaperlessAdapter, WebhookAdapter
from core.targets.adapters.system import EmailAdapter, SMBAdapter, SFTPAdapter


def normalize_target_type(target_type: str) -> str:
    normalized = (target_type or "").strip().lower().replace("_", "-")
    aliases = {
        "paperless-ngx": "paperless",
        "google drive": "google-drive",
        "googledrive": "google-drive",
        "one-drive": "onedrive",
        "next-cloud": "nextcloud",
    }
    return aliases.get(normalized, normalized)


_ADAPTERS: dict[str, DeliveryAdapter] = {
    "smb": SMBAdapter(),
    "sftp": SFTPAdapter(),
    "email": EmailAdapter(),
    "paperless": PaperlessAdapter(),
    "webhook": WebhookAdapter(),
    "google-drive": GoogleDriveAdapter(),
    "dropbox": DropboxAdapter(),
    "onedrive": OneDriveAdapter(),
    "nextcloud": NextcloudAdapter(),
}


def get_adapter(target_type: str) -> DeliveryAdapter | None:
    return _ADAPTERS.get(normalize_target_type(target_type))


def supported_target_types() -> list[str]:
    return sorted(_ADAPTERS)
