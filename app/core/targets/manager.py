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
import time

from app.core.targets.models import TargetConfig
from app.core.targets.repository import TargetRepository


class TargetManager:
    """Create, update, and test targets; delegate delivery."""

    def __init__(self):
        self.repo = TargetRepository()

    def list_targets(self) -> List[TargetConfig]:
        return self.repo.list()

    def create_target(self, target: TargetConfig, validate: bool = True) -> TargetConfig:
        """
        Create a new target.
        
        Args:
            target: Target configuration
            validate: If True, test connection before saving (default: True)
        
        Raises:
            Exception: If validation fails
        """
        if validate:
            # Test connection before saving
            validation_result = self._validate_target_config(target)
            if validation_result['status'] != 'ok':
                raise Exception(
                    f"Connection test failed: {validation_result.get('message', 'Unable to connect')}"
                )
        
        return self.repo.create(target)

    def update_target(self, target_id: str, target: TargetConfig, validate: bool = True) -> TargetConfig:
        """
        Update an existing target.
        
        Args:
            target_id: Target ID to update
            target: New target configuration
            validate: If True, test connection before saving (default: True)
        
        Raises:
            Exception: If validation fails
        """
        target.id = target_id  # Ensure ID matches
        
        if validate:
            # Test connection before updating
            validation_result = self._validate_target_config(target)
            if validation_result['status'] != 'ok':
                raise Exception(
                    f"Connection test failed: {validation_result.get('message', 'Unable to connect')}"
                )
        
        return self.repo.update(target)

    def delete_target(self, target_id: str) -> None:
        self.repo.delete(target_id)
    
    def _validate_target_config(self, target: TargetConfig) -> dict:
        """
        Validate target configuration by testing connectivity.
        
        Returns:
            dict with 'status' and optional 'message'
        """
        try:
            if target.type == 'SMB':
                # Test SMB connectivity with smbclient
                username = target.config.get('username', 'guest')
                password = target.config.get('password', '')
                connection = target.config.get('connection', '')
                
                if not connection:
                    return {"status": "error", "message": "Connection string is required"}
                
                print(f"Testing SMB connection to: {connection}")
                print(f"Username: {username}")
                
                # Parse connection string - can be //server/share or \\server\share
                # Convert Windows format to Unix format
                connection_unix = connection.replace('\\', '/')
                if not connection_unix.startswith('//'):
                    connection_unix = '//' + connection_unix
                
                # Extract server for -L command (just list shares, don't access)
                # Format: //server/share -> just use //server for listing
                server = connection_unix.split('/')[2] if len(connection_unix.split('/')) > 2 else connection_unix
                
                print(f"Testing server: //{server}")
                
                try:
                    # Build smbclient command
                    # Format: smbclient -L //server -U username%password
                    # Do NOT use -N (no password) flag if password is provided
                    cmd = ['smbclient', '-L', f'//{server}', '-U', f"{username}%{password}"]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=10,
                        text=True
                    )
                    
                    print(f"smbclient exit code: {result.returncode}")
                    print(f"stdout: {result.stdout[:200]}")
                    print(f"stderr: {result.stderr[:200]}")
                    
                    if result.returncode == 0:
                        return {"status": "ok"}
                    else:
                        # Check both stdout and stderr for error messages
                        error_output = result.stderr + result.stdout
                        error_msg = error_output.strip() if error_output.strip() else "Connection failed"
                        
                        # Common errors and user-friendly messages
                        if "NT_STATUS_LOGON_FAILURE" in error_output:
                            error_msg = f"Login failed - check username and password for {server}"
                        elif "NT_STATUS_HOST_UNREACHABLE" in error_output or "NT_STATUS_IO_TIMEOUT" in error_output:
                            error_msg = f"Server {server} not reachable - check IP address and network"
                        elif "NT_STATUS_BAD_NETWORK_NAME" in error_output:
                            error_msg = f"Share not found on {server}"
                        elif "NT_STATUS_ACCESS_DENIED" in error_output:
                            error_msg = f"Access denied - check permissions for user {username}"
                        
                        print(f"SMB validation failed: {error_msg}")
                        return {"status": "error", "message": error_msg}
                except FileNotFoundError:
                    return {"status": "error", "message": "smbclient not installed. Install with: sudo apt install smbclient"}
                except subprocess.TimeoutExpired:
                    return {"status": "error", "message": f"Connection timeout - server {server} not responding"}
                
            elif target.type == 'SFTP':
                # Test SFTP with ssh
                host = target.config.get('host', target.config.get('connection', '').split('@')[-1])
                port = target.config.get('port', 22)
                username = target.config.get('username', target.config.get('connection', '').split('@')[0] if '@' in target.config.get('connection', '') else 'root')
                password = target.config.get('password', '')
                
                if not host:
                    return {"status": "error", "message": "Host is required"}
                
                try:
                    if password:
                        # Test with password using sshpass
                        result = subprocess.run(
                            ['sshpass', '-p', password, 'ssh', '-o', 'StrictHostKeyChecking=no',
                             '-p', str(port), '-o', 'ConnectTimeout=5', f'{username}@{host}', 'exit'],
                            capture_output=True,
                            timeout=10,
                            text=True
                        )
                    else:
                        # Test with SSH key
                        result = subprocess.run(
                            ['ssh', '-o', 'BatchMode=yes', '-p', str(port), '-o', 'ConnectTimeout=5', 
                             f'{username}@{host}', 'exit'],
                            capture_output=True,
                            timeout=10,
                            text=True
                        )
                    
                    if result.returncode == 0:
                        return {"status": "ok"}
                    else:
                        return {"status": "error", "message": "SSH connection failed. Check host and credentials."}
                except FileNotFoundError:
                    if password:
                        return {"status": "error", "message": "sshpass not installed. Install with: sudo apt install sshpass"}
                    else:
                        return {"status": "error", "message": "ssh not installed"}
                
            elif target.type == 'Email':
                # Test SMTP connection and authentication
                smtp_host = target.config.get('smtp_host', 'localhost')
                smtp_port = target.config.get('smtp_port', 587)
                username = target.config.get('username')
                password = target.config.get('password')
                use_tls = target.config.get('use_tls', True)
                
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.quit()
                return {"status": "ok"}
                
            elif target.type in ['Paperless-ngx', 'Webhook']:
                # Test HTTP endpoint
                url = target.config.get('connection', '')
                if not url:
                    return {"status": "error", "message": "URL is required"}
                
                response = requests.head(url, timeout=5)
                
                if response.status_code < 500:
                    return {"status": "ok"}
                else:
                    return {"status": "error", "message": f"Server error: {response.status_code}"}
                
            else:
                # Unknown type - skip validation
                return {"status": "ok"}
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Connection timeout - server not reachable"}
        except FileNotFoundError as e:
            return {"status": "error", "message": f"Required tool not installed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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

    def deliver(self, target_id: str, file_path: str, metadata: dict, max_retries: int = 3) -> None:
        """
        Deliver scanned file to target destination with retry logic.
        
        Args:
            target_id: Target identifier
            file_path: Path to file to deliver
            metadata: Additional metadata for delivery
            max_retries: Maximum number of retry attempts (default: 3)
        
        Raises:
            Exception: If delivery fails after all retries
        """
        target = self.repo.get(target_id)
        if not target or not target.enabled:
            raise Exception(f"Target {target_id} not found or disabled")
        
        file = Path(file_path)
        if not file.exists():
            raise Exception(f"File {file_path} not found")
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"Delivery attempt {attempt + 1}/{max_retries} to {target.name}")
                
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
                elif target.type == 'Google Drive':
                    self._deliver_google_drive(target, file)
                elif target.type == 'Dropbox':
                    self._deliver_dropbox(target, file)
                elif target.type == 'OneDrive':
                    self._deliver_onedrive(target, file)
                elif target.type == 'Nextcloud':
                    self._deliver_nextcloud(target, file)
                else:
                    raise Exception(f"Unsupported target type: {target.type}")
                
                print(f"✓ Delivery to {target.name} successful")
                return  # Success!
                
            except Exception as e:
                last_error = e
                print(f"✗ Delivery attempt {attempt + 1} failed: {str(e)}")
                
                # Don't retry on final attempt
                if attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s...
                    delay = 2 ** attempt
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"All {max_retries} delivery attempts failed")
        
        # All retries failed
        raise Exception(f"Delivery to {target.name} failed after {max_retries} attempts: {last_error}")
    
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
        host = target.config.get('host', target.config['connection'].split('@')[-1] if '@' in target.config['connection'] else target.config['connection'])
        port = target.config.get('port', 22)
        username = target.config.get('username', target.config['connection'].split('@')[0] if '@' in target.config['connection'] else 'root')
        password = target.config.get('password', '')
        remote_path = target.config.get('remote_path', '.')
        
        # Build SFTP batch command
        cmd = f'put "{file}" "{remote_path}/{file.name}"'
        
        if password:
            # Use sshpass for password authentication
            try:
                result = subprocess.run(
                    ['sshpass', '-p', password, 'sftp', '-o', 'StrictHostKeyChecking=no', 
                     '-P', str(port), '-b', '-', f'{username}@{host}'],
                    input=cmd.encode(),
                    capture_output=True,
                    timeout=60
                )
            except FileNotFoundError:
                raise Exception("sshpass not installed. Install with: sudo apt install sshpass")
        else:
            # Use SSH key authentication (no password)
            result = subprocess.run(
                ['sftp', '-P', str(port), '-b', '-', f'{username}@{host}'],
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
    
    def _deliver_google_drive(self, target: TargetConfig, file: Path) -> None:
        """Upload to Google Drive."""
        from app.core.targets.cloud import GoogleDriveHandler
        GoogleDriveHandler.upload(file, target.config)
    
    def _deliver_dropbox(self, target: TargetConfig, file: Path) -> None:
        """Upload to Dropbox."""
        from app.core.targets.cloud import DropboxHandler
        DropboxHandler.upload(file, target.config)
    
    def _deliver_onedrive(self, target: TargetConfig, file: Path) -> None:
        """Upload to OneDrive."""
        from app.core.targets.cloud import OneDriveHandler
        OneDriveHandler.upload(file, target.config)
    
    def _deliver_nextcloud(self, target: TargetConfig, file: Path) -> None:
        """Upload to Nextcloud/ownCloud."""
        from app.core.targets.cloud import NextcloudHandler
        NextcloudHandler.upload(file, target.config)
