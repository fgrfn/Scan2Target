"""Target management and delivery handlers."""
from __future__ import annotations
from typing import List
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import requests

from app.core.targets.models import TargetConfig
from app.core.targets.repository import TargetRepository


class TargetManager:
    """Create, update, and test targets; delegate delivery."""

    def __init__(self):
        self.repo = TargetRepository()

    def list_targets(self) -> List[TargetConfig]:
        return self.repo.list()

    def create_target(self, target: TargetConfig) -> TargetConfig:
        return self.repo.create(target)

    def update_target(self, target_id: str, target: TargetConfig) -> TargetConfig:
        target.id = target_id  # Ensure ID matches
        return self.repo.update(target)

    def delete_target(self, target_id: str) -> None:
        self.repo.delete(target_id)

    def test_target(self, target_id: str) -> dict:
        """Test connectivity to a target."""
        target = self.repo.get(target_id)
        if not target:
            return {"target_id": target_id, "status": "error", "message": "Target not found"}
        
        try:
            if target.type == 'SMB':
                # Test SMB connectivity with smbclient
                result = subprocess.run(
                    ['smbclient', '-L', target.config['connection'], '-U', 
                     f"{target.config.get('username', 'guest')}%{target.config.get('password', '')}",
                     '-N'],
                    capture_output=True,
                    timeout=10
                )
                status = "ok" if result.returncode == 0 else "error"
                
            elif target.type == 'SFTP':
                # Test SFTP with ssh
                host = target.config['connection']
                result = subprocess.run(
                    ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', host, 'exit'],
                    capture_output=True,
                    timeout=10
                )
                status = "ok" if result.returncode == 0 else "error"
                
            elif target.type == 'Email':
                # Test SMTP connection
                smtp_host = target.config.get('smtp_host', 'localhost')
                smtp_port = target.config.get('smtp_port', 587)
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
                server.quit()
                status = "ok"
                
            elif target.type in ['Paperless-ngx', 'Webhook']:
                # Test HTTP endpoint
                url = target.config['connection']
                response = requests.head(url, timeout=5)
                status = "ok" if response.status_code < 500 else "error"
                
            else:
                status = "unknown"
                
            return {"target_id": target_id, "status": status}
            
        except Exception as e:
            return {"target_id": target_id, "status": "error", "message": str(e)}

    def deliver(self, target_id: str, file_path: str, metadata: dict) -> None:
        """Deliver scanned file to target destination."""
        target = self.repo.get(target_id)
        if not target or not target.enabled:
            raise Exception(f"Target {target_id} not found or disabled")
        
        file = Path(file_path)
        if not file.exists():
            raise Exception(f"File {file_path} not found")
        
        try:
            if target.type == 'SMB':
                self._deliver_smb(target, file)
            elif target.type == 'SFTP':
                self._deliver_sftp(target, file)
            elif target.type == 'Email':
                self._deliver_email(target, file, metadata)
            elif target.type == 'Paperless-ngx':
                self._deliver_paperless(target, file, metadata)
            elif target.type == 'Webhook':
                self._deliver_webhook(target, file, metadata)
            else:
                raise Exception(f"Unsupported target type: {target.type}")
        except Exception as e:
            raise Exception(f"Delivery to {target.name} failed: {e}")
    
    def _deliver_smb(self, target: TargetConfig, file: Path) -> None:
        """Upload file to SMB share."""
        username = target.config.get('username', 'guest')
        password = target.config.get('password', '')
        share = target.config['connection']
        
        # Use smbclient to upload
        cmd = [
            'smbclient', share,
            '-U', f"{username}%{password}",
            '-c', f'put "{file}" "{file.name}"'
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"smbclient failed: {result.stderr.decode()}")
    
    def _deliver_sftp(self, target: TargetConfig, file: Path) -> None:
        """Upload file via SFTP."""
        host = target.config['connection']
        remote_path = target.config.get('remote_path', '.')
        
        # Use sftp command
        cmd = f'put "{file}" "{remote_path}/{file.name}"'
        result = subprocess.run(
            ['sftp', '-b', '-', host],
            input=cmd.encode(),
            capture_output=True,
            timeout=60
        )
        if result.returncode != 0:
            raise Exception(f"sftp failed: {result.stderr.decode()}")
    
    def _deliver_email(self, target: TargetConfig, file: Path, metadata: dict) -> None:
        """Send file via email."""
        smtp_host = target.config.get('smtp_host', 'localhost')
        smtp_port = target.config.get('smtp_port', 587)
        from_addr = target.config.get('from', 'raspscan@localhost')
        to_addr = target.config['connection']  # email address
        
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = f"RaspScan: {file.name}"
        
        # Attach file
        with open(file, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{file.name}"')
            msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(smtp_host, smtp_port)
        if target.config.get('use_tls', True):
            server.starttls()
        if target.config.get('username') and target.config.get('password'):
            server.login(target.config['username'], target.config['password'])
        server.send_message(msg)
        server.quit()
    
    def _deliver_paperless(self, target: TargetConfig, file: Path, metadata: dict) -> None:
        """Upload to Paperless-ngx via API."""
        url = target.config['connection'].rstrip('/') + '/api/documents/post_document/'
        token = target.config.get('api_token', '')
        
        headers = {'Authorization': f'Token {token}'} if token else {}
        
        with open(file, 'rb') as f:
            files = {'document': (file.name, f, 'application/pdf')}
            response = requests.post(url, files=files, headers=headers, timeout=30)
            response.raise_for_status()
    
    def _deliver_webhook(self, target: TargetConfig, file: Path, metadata: dict) -> None:
        """POST file to webhook endpoint."""
        url = target.config['connection']
        
        with open(file, 'rb') as f:
            files = {'file': (file.name, f)}
            data = metadata
            response = requests.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
