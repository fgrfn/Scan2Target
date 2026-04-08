from __future__ import annotations
import subprocess
from pathlib import Path
from .base import BaseProvider


class SMBProvider(BaseProvider):
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize SMB share path to smbclient format (//server/share).

        Accepts Windows UNC paths (\\\\server\\share or \\\\server\\share)
        and converts them to forward-slash format required by smbclient.
        """
        p = path.strip().replace("\\", "/")
        # Collapse any leading slashes beyond two (///server → //server)
        while p.startswith("///"):
            p = p[1:]
        if not p.startswith("//"):
            p = "//" + p.lstrip("/")
        return p

    def _cmd(self, config: dict, args: list[str]) -> list[str]:
        connection = self._normalize_path(config["connection"])
        return ["smbclient", connection,
                "-U", f"{config['username']}%{config['password']}",
                "-c", " ".join(args)]

    def test(self, config: dict) -> None:
        r = subprocess.run(self._cmd(config, ["ls"]),
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            err = r.stderr.strip() or r.stdout.strip()
            # Provide a more actionable message for common SMB errors
            if "NT_STATUS_BAD_NETWORK_NAME" in err:
                share = self._normalize_path(config["connection"])
                raise ConnectionError(
                    f"SMB error: Share not found — check that '{share}' exists on the server "
                    f"(NT_STATUS_BAD_NETWORK_NAME)"
                )
            raise ConnectionError(f"SMB error: {err}")

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        r = subprocess.run(self._cmd(config, [f"put {file_path} {filename}"]),
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"SMB upload failed: {r.stderr.strip()}")
