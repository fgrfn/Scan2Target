"""Cloud storage providers: Google Drive, Dropbox, OneDrive, Nextcloud."""
from __future__ import annotations
import json
from pathlib import Path
import requests
from .base import BaseProvider


class GoogleDriveProvider(BaseProvider):
    _BASE = "https://www.googleapis.com/upload/drive/v3/files"
    _META = "https://www.googleapis.com/drive/v3/files"

    def _headers(self, config: dict) -> dict:
        return {"Authorization": f"Bearer {config['access_token']}"}

    def test(self, config: dict) -> None:
        r = requests.get(f"{self._META}?pageSize=1", headers=self._headers(config), timeout=10)
        if r.status_code == 401:
            raise ConnectionError("Google Drive: invalid or expired access token")
        if not r.ok:
            raise ConnectionError(f"Google Drive: {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        meta = {"name": filename}
        if config.get("folder_id"):
            meta["parents"] = [config["folder_id"]]
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{self._BASE}?uploadType=multipart",
                headers=self._headers(config),
                files={"metadata": (None, json.dumps(meta), "application/json"),
                       "file": (filename, f)},
                timeout=120,
            )
        if not r.ok:
            raise RuntimeError(f"Google Drive upload failed: {r.status_code} {r.text[:200]}")


class DropboxProvider(BaseProvider):
    def _headers(self, config: dict) -> dict:
        return {"Authorization": f"Bearer {config['access_token']}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps({
                    "path": f"{config.get('path','')}/{config.get('_filename','')}",
                    "mode": "add", "autorename": True})}

    def test(self, config: dict) -> None:
        r = requests.post("https://api.dropboxapi.com/2/users/get_current_account",
                          headers={"Authorization": f"Bearer {config['access_token']}"}, timeout=10)
        if r.status_code == 401:
            raise ConnectionError("Dropbox: invalid or expired access token")
        if not r.ok:
            raise ConnectionError(f"Dropbox: {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        path = f"{config.get('path', '')}/{filename}".replace("//", "/")
        with open(file_path, "rb") as f:
            r = requests.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers={"Authorization": f"Bearer {config['access_token']}",
                         "Content-Type": "application/octet-stream",
                         "Dropbox-API-Arg": json.dumps({"path": path, "mode": "add", "autorename": True})},
                data=f, timeout=120,
            )
        if not r.ok:
            raise RuntimeError(f"Dropbox upload failed: {r.status_code} {r.text[:200]}")


class OneDriveProvider(BaseProvider):
    _BASE = "https://graph.microsoft.com/v1.0/me/drive/root:"

    def _headers(self, config: dict) -> dict:
        return {"Authorization": f"Bearer {config['access_token']}"}

    def test(self, config: dict) -> None:
        r = requests.get("https://graph.microsoft.com/v1.0/me/drive",
                         headers=self._headers(config), timeout=10)
        if r.status_code == 401:
            raise ConnectionError("OneDrive: invalid or expired access token")
        if not r.ok:
            raise ConnectionError(f"OneDrive: {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        path = config.get("path", "/Scans")
        url = f"{self._BASE}{path}/{filename}:/content"
        with open(file_path, "rb") as f:
            r = requests.put(url, headers=self._headers(config), data=f, timeout=120)
        if not r.ok:
            raise RuntimeError(f"OneDrive upload failed: {r.status_code} {r.text[:200]}")


class NextcloudProvider(BaseProvider):
    def _url(self, config: dict, filename: str) -> str:
        base = config["webdav_url"].rstrip("/")
        path = config.get("path", "/Scans").rstrip("/")
        return f"{base}{path}/{filename}"

    def test(self, config: dict) -> None:
        r = requests.request("PROPFIND", config["webdav_url"],
                             auth=(config["username"], config["password"]), timeout=10)
        if r.status_code == 401:
            raise ConnectionError("Nextcloud: invalid credentials")
        if r.status_code not in (200, 207):
            raise ConnectionError(f"Nextcloud: {r.status_code}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        with open(file_path, "rb") as f:
            r = requests.put(self._url(config, filename),
                             auth=(config["username"], config["password"]),
                             data=f, timeout=120)
        if r.status_code not in (200, 201, 204):
            raise RuntimeError(f"Nextcloud upload failed: {r.status_code} {r.text[:200]}")
