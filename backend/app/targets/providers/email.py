from __future__ import annotations
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from .base import BaseProvider


class EmailProvider(BaseProvider):
    def _connect(self, config: dict) -> smtplib.SMTP:
        host = config["smtp_host"]
        port = int(config.get("smtp_port", 587))
        use_tls = config.get("use_tls", True)
        ctx = ssl.create_default_context()
        if port == 465:
            smtp = smtplib.SMTP_SSL(host, port, context=ctx, timeout=15)
        else:
            smtp = smtplib.SMTP(host, port, timeout=15)
            if use_tls:
                smtp.starttls(context=ctx)
        smtp.login(config["username"], config["password"])
        return smtp

    def test(self, config: dict) -> None:
        smtp = self._connect(config)
        smtp.quit()

    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        to = config.get("to", config["username"])
        msg = MIMEMultipart()
        msg["From"] = config["username"]
        msg["To"] = to
        msg["Subject"] = f"Scan: {filename}"
        msg.attach(MIMEText("Scan attached.", "plain"))
        with open(file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)
        smtp = self._connect(config)
        smtp.sendmail(config["username"], to, msg.as_string())
        smtp.quit()
