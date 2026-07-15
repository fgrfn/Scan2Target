"""SMB, SFTP and SMTP delivery adapters."""
from __future__ import annotations

import os
import smtplib
import subprocess
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any

from core.targets.adapters.base import DeliveryAdapter
from core.targets.models import EmailConfig, SMBConfig, SFTPConfig, TargetConfig


def parse_smb_connection(connection: str) -> tuple[str, str, str]:
    normalized = (connection or "").replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) < 2:
        raise ValueError("SMB connection must be //server/share[/path]")
    return parts[0], parts[1], "/".join(parts[2:])


def _smb_credentials(username: str, password: str):
    handle = tempfile.NamedTemporaryFile("w", prefix="scan2target-smb-", delete=False)
    try:
        handle.write(f"username = {username}\npassword = {password}\n")
        handle.close()
        os.chmod(handle.name, 0o600)
        return handle.name
    except Exception:
        Path(handle.name).unlink(missing_ok=True)
        raise


class SMBAdapter(DeliveryAdapter):
    config_model = SMBConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        result["connection"] = result.get("connection") or result.get("path") or result.get("url")
        return result

    def _run(self, target: TargetConfig, command: str, timeout: int) -> subprocess.CompletedProcess:
        config = self.parse_config(target)
        server, share, _ = parse_smb_connection(config.connection)
        credentials = _smb_credentials(config.username, config.password)
        try:
            return subprocess.run(
                ["smbclient", f"//{server}/{share}", "-A", credentials, "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        finally:
            Path(credentials).unlink(missing_ok=True)

    def validate(self, target: TargetConfig) -> dict:
        try:
            result = self._run(target, "ls", 10)
            if result.returncode == 0:
                return {"status": "ok", "message": "SMB share reachable"}
            return {"status": "error", "message": (result.stderr or result.stdout).strip()[:300]}
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        _, _, base_path = parse_smb_connection(config.connection)
        destination = f"{base_path.strip('/')}/{file.name}" if base_path else file.name
        commands: list[str] = []
        if "/" in destination:
            commands.append(f'mkdir "{destination.rsplit("/", 1)[0]}"')
        commands.append(f'put "{file}" "{destination}"')
        result = self._run(target, "; ".join(commands), 60)
        if result.returncode != 0:
            raise RuntimeError(f"SMB upload failed: {(result.stderr or result.stdout).strip()[:300]}")


class SFTPAdapter(DeliveryAdapter):
    config_model = SFTPConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        connection = str(result.get("connection") or "")
        if not result.get("host"):
            result["host"] = connection.split("@")[-1]
        if not result.get("username") and "@" in connection:
            result["username"] = connection.split("@", 1)[0]
        return result

    @staticmethod
    def _host_key_args(strict: bool) -> list[str]:
        return ["-o", f"StrictHostKeyChecking={'yes' if strict else 'no'}"]

    def _command(self, config: SFTPConfig, executable: str) -> tuple[list[str], dict[str, str]]:
        args = [executable, *self._host_key_args(config.strict_host_key_checking)]
        env = os.environ.copy()
        if config.password:
            env["SSHPASS"] = config.password
            args = ["sshpass", "-e", *args]
        return args, env

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            args, env = self._command(config, "ssh")
            args.extend(
                ["-p", str(config.port), "-o", "ConnectTimeout=5", f"{config.username}@{config.host}", "exit"]
            )
            result = subprocess.run(args, capture_output=True, text=True, timeout=10, env=env)
            if result.returncode == 0:
                return {"status": "ok", "message": "SFTP host reachable"}
            return {"status": "error", "message": (result.stderr or result.stdout).strip()[:300]}
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        args, env = self._command(config, "sftp")
        args.extend(["-P", str(config.port), "-b", "-", f"{config.username}@{config.host}"])
        remote = f"{config.remote_path.rstrip('/')}/{file.name}"
        result = subprocess.run(
            args,
            input=f'put "{file}" "{remote}"\n',
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(f"SFTP upload failed: {result.stderr.strip()[:300]}")


class EmailAdapter(DeliveryAdapter):
    config_model = EmailConfig

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = dict(config)
        result["to"] = result.get("to") or result.get("connection")
        result["from_address"] = result.get("from_address") or result.get("from") or "scan2target@localhost"
        return result

    def _connect(self, config: EmailConfig) -> smtplib.SMTP:
        server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10)
        if config.use_tls:
            server.starttls()
        if config.username and config.password:
            server.login(config.username, config.password)
        return server

    def validate(self, target: TargetConfig) -> dict:
        try:
            config = self.parse_config(target)
            server = self._connect(config)
            server.quit()
            return {"status": "ok", "message": "SMTP connection successful"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        config = self.parse_config(target)
        message = MIMEMultipart()
        message["From"] = config.from_address
        message["To"] = config.to
        message["Subject"] = f"Scan2Target: {file.name}"
        with file.open("rb") as stream:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(stream.read())
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", f'attachment; filename="{file.name}"')
        message.attach(attachment)
        server = self._connect(config)
        try:
            server.send_message(message)
        finally:
            server.quit()
