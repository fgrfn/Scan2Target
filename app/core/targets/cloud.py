"""Cloud storage upload handlers used by target adapters."""
from __future__ import annotations

import json
from pathlib import Path

import requests


class GoogleDriveHandler:
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        access_token = config.get("access_token")
        if not access_token:
            raise ValueError("Google Drive access_token required")
        metadata = {"name": file_path.name}
        if config.get("folder_id"):
            metadata["parents"] = [config["folder_id"]]
        headers = {"Authorization": f"Bearer {access_token}"}
        with file_path.open("rb") as stream:
            response = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers=headers,
                files={
                    "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
                    "file": (file_path.name, stream),
                },
                timeout=60,
            )
        response.raise_for_status()


class DropboxHandler:
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        access_token = config.get("access_token")
        if not access_token:
            raise ValueError("Dropbox access_token required")
        target_path = config.get("path") or "/scans"
        dropbox_path = f"{target_path.rstrip('/')}/{file_path.name}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps(
                {"path": dropbox_path, "mode": "add", "autorename": True, "mute": False}
            ),
        }
        with file_path.open("rb") as stream:
            response = requests.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers=headers,
                data=stream,
                timeout=60,
            )
        response.raise_for_status()


class OneDriveHandler:
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        access_token = config.get("access_token")
        if not access_token:
            raise ValueError("OneDrive access_token required")
        target_path = config.get("path") or "/Scans"
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:{target_path}/{file_path.name}:/content"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
        }
        with file_path.open("rb") as stream:
            response = requests.put(url, headers=headers, data=stream, timeout=60)
        response.raise_for_status()


class NextcloudHandler:
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        url = str(config.get("url") or "").rstrip("/")
        username = config.get("username")
        password = config.get("password")
        target_path = config.get("path") or "/Scans"
        if not all([url, username, password]):
            raise ValueError("Nextcloud url, username, and password required")
        webdav_url = f"{url}/remote.php/dav/files/{username}{target_path}/{file_path.name}"
        with file_path.open("rb") as stream:
            response = requests.put(
                webdav_url,
                auth=(username, password),
                data=stream,
                timeout=60,
            )
        response.raise_for_status()
