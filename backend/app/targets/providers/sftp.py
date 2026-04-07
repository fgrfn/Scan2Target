from __future__ import annotations
import subprocess
from pathlib import Path
from .base import BaseProvider


class SFTPProvider(BaseProvider):
    def _base_cmd(self, config: dict) -> list[str]:
        host = config["host"]
        port = config.get("port", 22)
        user = config["username"]
        cmd = []
        password = config.get("password")
        if password:
            cmd = ["sshpass", "-p", password]
        cmd += ["sftp", "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=no", "-P", str(port),
                f"{user}@{host}"]
        return cmd

    def test(self, config: dict) -> None:
        r = subprocess.run(self._base_cmd(config), input="exit\n",
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            raise ConnectionError(f"SFTP error: {r.stderr.strip()}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        path = config.get("path", "/")
        r = subprocess.run(self._base_cmd(config),
                           input=f"put {file_path} {path}/{filename}\nexit\n",
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"SFTP upload failed: {r.stderr.strip()}")
