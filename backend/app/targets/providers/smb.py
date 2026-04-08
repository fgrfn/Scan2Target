from __future__ import annotations
import subprocess
from pathlib import Path
from .base import BaseProvider


class SMBProvider(BaseProvider):
    def _cmd(self, config: dict, args: list[str]) -> list[str]:
        return ["smbclient", config["connection"],
                "-U", f"{config['username']}%{config['password']}",
                "-c", " ".join(args)]

    def test(self, config: dict) -> None:
        r = subprocess.run(self._cmd(config, ["ls"]),
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            raise ConnectionError(f"SMB error: {r.stderr.strip() or r.stdout.strip()}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        r = subprocess.run(self._cmd(config, [f"put {file_path} {filename}"]),
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"SMB upload failed: {r.stderr.strip()}")
