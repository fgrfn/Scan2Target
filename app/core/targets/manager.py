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
    
    @staticmethod
    def _parse_smb_connection(connection: str) -> tuple[str, str, str]:
        """
        Parse SMB connection string into server, share, and path components.
        
        Supports multiple formats:
        - //server/share/path
        - \\\\server\\share\\path
        - server/share/path
        - 192.168.1.100/sharename
        
        Returns:
            (server, share_name, path) tuple
        """
        if not connection:
            raise ValueError("Connection string is empty")
        
        # Normalize to Unix format: replace backslashes with forward slashes
        normalized = connection.replace('\\', '/')
        
        # Remove leading slashes
        normalized = normalized.lstrip('/')
        
        # Split into parts
        parts = normalized.split('/')
        
        if len(parts) < 2:
            raise ValueError(f"Invalid SMB path format: '{connection}'. Expected format: //server/share or server/share")
        
        server = parts[0]
        share_name = parts[1]
        path = '/'.join(parts[2:]) if len(parts) > 2 else ''
        
        # Validate server (IP or hostname)
        if not server:
            raise ValueError("Server name/IP is required")
        
        # Validate share name
        if not share_name:
            raise ValueError("Share name is required")
        
        return server, share_name, path

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
                
                print(f"[SMB] Testing connection to: {connection}")
                print(f"[SMB] Username: {username}")
                
                # Parse connection string robustly
                try:
                    server, share_name, path = self._parse_smb_connection(connection)
                    print(f"[SMB] Parsed - Server: {server}, Share: {share_name}, Path: {path}")
                except ValueError as e:
                    return {"status": "error", "message": str(e)}
                
                # Build full share path for smbclient
                share_path = f"//{server}/{share_name}"
                print(f"[SMB] Testing share path: {share_path}")
                
                try:
                    # Test by trying to list files in the share (more accurate than -L)
                    # Format: smbclient //server/share -U username%password -c 'ls'
                    cmd = ['smbclient', share_path, '-U', f"{username}%{password}", '-c', 'ls']
                    
                    print(f"[SMB] Running command: {' '.join(cmd[:3])} [credentials hidden] -c 'ls'")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=10,
                        text=True
                    )
                    
                    print(f"[SMB] Exit code: {result.returncode}")
                    print(f"[SMB] stdout: {result.stdout[:200]}")
                    print(f"[SMB] stderr: {result.stderr[:200]}")
                    
                    if result.returncode == 0:
                        return {"status": "ok", "message": f"Successfully connected to {share_path}"}
                    else:
                        # Check both stdout and stderr for error messages
                        error_output = result.stderr + result.stdout
                        error_msg = error_output.strip() if error_output.strip() else "Connection failed"
                        
                        # Common errors and user-friendly messages
                        if "NT_STATUS_LOGON_FAILURE" in error_output:
                            error_msg = f"Login failed - check username and password (Server: {server}, User: {username})"
                        elif "NT_STATUS_HOST_UNREACHABLE" in error_output or "NT_STATUS_IO_TIMEOUT" in error_output:
                            error_msg = f"Server '{server}' not reachable - check IP/hostname and network connection"
                        elif "NT_STATUS_BAD_NETWORK_NAME" in error_output:
                            error_msg = f"Share '{share_name}' not found on server '{server}' - check share name"
                        elif "NT_STATUS_ACCESS_DENIED" in error_output:
                            error_msg = f"Access denied to '{share_path}' for user '{username}' - check permissions"
                        elif "NT_STATUS_OBJECT_NAME_NOT_FOUND" in error_output:
                            error_msg = f"Path '{path}' not found in share '{share_name}' - check folder path"
                        elif "Connection to" in error_output and "failed" in error_output:
                            error_msg = f"Cannot connect to '{server}' - check if SMB is enabled and firewall allows connection"
                        
                        print(f"[SMB] Validation failed: {error_msg}")
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
                
            elif target.type == 'Paperless-ngx':
                # Test Paperless-ngx API endpoint
                url = target.config.get('connection', '').rstrip('/')
                if not url:
                    return {"status": "error", "message": "Paperless-ngx URL is required"}
                
                token = target.config.get('api_token') or target.config.get('token', '')
                if not token:
                    return {"status": "error", "message": "API token is required"}
                
                # Test API endpoint
                api_url = url + '/api/'
                headers = {'Authorization': f'Token {token}'}
                
                try:
                    response = requests.get(api_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        return {"status": "ok", "message": "Successfully connected to Paperless-ngx"}
                    elif response.status_code == 401:
                        return {"status": "error", "message": "Authentication failed - check API token"}
                    elif response.status_code == 403:
                        return {"status": "error", "message": "Access forbidden - check API token permissions"}
                    else:
                        return {"status": "error", "message": f"Server returned status {response.status_code}"}
                except requests.exceptions.ConnectionError:
                    return {"status": "error", "message": "Cannot connect to Paperless-ngx - check URL"}
                except requests.exceptions.Timeout:
                    return {"status": "error", "message": "Connection timeout"}
                
            elif target.type == 'Webhook':
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
                # Test SMB connectivity by attempting to create and delete a test file
                import tempfile
                
                # Create a small test file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                    tmp.write('Scan2Target connection test')
                    test_file = tmp.name
                
                try:
                    # Try to upload the test file
                    username = target.config.get('username', 'guest')
                    password = target.config.get('password', '')
                    connection = target.config.get('connection', '')
                    
                    if not connection:
                        return {"target_id": target_id, "status": "error", "message": "Connection string is missing"}
                    
                    # Parse connection using the robust parser
                    try:
                        server, share_name, base_path = self._parse_smb_connection(connection)
                        share_path = f"//{server}/{share_name}"
                    except ValueError as e:
                        return {"target_id": target_id, "status": "error", "message": f"Invalid connection format: {e}"}
                    
                    print(f"[SMB Test] Testing upload to: {share_path}")
                    print(f"[SMB Test] Base path in share: {base_path if base_path else '(root)'}") 
                    print(f"[SMB Test] Username: {username}")
                    
                    # Test file name with path if base_path exists
                    test_filename = f".scan2target_test_{int(time.time())}.txt"
                    if base_path:
                        test_filename = f"{base_path}/{test_filename}"
                    
                    print(f"[SMB Test] Test file path: {test_filename}")
                    
                    # Try to upload and then delete the test file
                    result = subprocess.run(
                        ['smbclient', share_path, '-U', f"{username}%{password}", 
                         '-c', f'put "{test_file}" "{test_filename}"; del "{test_filename}"'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    print(f"[SMB Test] Exit code: {result.returncode}")
                    print(f"[SMB Test] stdout: {result.stdout[:300]}")
                    print(f"[SMB Test] stderr: {result.stderr[:300]}")
                    
                    if result.returncode == 0:
                        status = "ok"
                        message = None
                    else:
                        status = "error"
                        # Combine stderr and stdout for better error messages
                        error_output = (result.stderr + result.stdout).strip()
                        
                        # Parse common SMB errors
                        if "NT_STATUS_LOGON_FAILURE" in error_output:
                            message = "Login failed - check username and password"
                        elif "NT_STATUS_BAD_NETWORK_NAME" in error_output:
                            message = f"Share not found: {share_path}"
                        elif "NT_STATUS_ACCESS_DENIED" in error_output:
                            message = f"Access denied - check permissions for user {username}"
                        elif "NT_STATUS_HOST_UNREACHABLE" in error_output or "NT_STATUS_IO_TIMEOUT" in error_output:
                            message = "Server not reachable - check IP address and network"
                        elif "NT_STATUS_OBJECT_NAME_NOT_FOUND" in error_output:
                            message = "Cannot create file - check share path and permissions"
                        else:
                            # Generic error with cleaned message
                            message = error_output[:200] if error_output else "Connection test failed"
                    
                finally:
                    # Clean up test file
                    Path(test_file).unlink(missing_ok=True)
                
            elif target.type == 'SFTP':
                # Test SFTP with ssh
                host = target.config['connection']
                result = subprocess.run(
                    ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', host, 'exit'],
                    capture_output=True,
                    timeout=10
                )
                status = "ok" if result.returncode == 0 else "error"
                message = None
                
            elif target.type == 'Email':
                # Test SMTP connection
                smtp_host = target.config.get('smtp_host', 'localhost')
                smtp_port = target.config.get('smtp_port', 587)
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
                server.quit()
                status = "ok"
                message = None
                
            elif target.type == 'Paperless-ngx':
                # Test Paperless-ngx API
                url = target.config['connection'].rstrip('/')
                token = target.config.get('api_token') or target.config.get('token', '')
                headers = {'Authorization': f'Token {token}'} if token else {}
                api_url = url + '/api/'
                response = requests.get(api_url, headers=headers, timeout=5)
                status = "ok" if response.status_code == 200 else "error"
                message = f"Status code: {response.status_code}" if status == "error" else None
                
            elif target.type == 'Webhook':
                # Test HTTP endpoint
                url = target.config['connection']
                response = requests.head(url, timeout=5)
                status = "ok" if response.status_code < 500 else "error"
                message = None
                
            else:
                status = "unknown"
                message = "Target type not supported for testing"
                
            result = {"target_id": target_id, "status": status}
            if message:
                result["message"] = message
            return result
            
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
        """Upload file to SMB share with robust path handling."""
        username = target.config.get('username', 'guest')
        password = target.config.get('password', '')
        connection = target.config['connection']
        upload_path = target.config.get('upload_path', '')
        
        print(f"[SMB] Delivering file: {file.name}")
        print(f"[SMB] Connection: {connection}")
        print(f"[SMB] Upload path: {upload_path}")
        
        # Parse connection string
        try:
            server, share_name, base_path = self._parse_smb_connection(connection)
        except ValueError as e:
            raise Exception(f"Invalid SMB connection string: {e}")
        
        # Build full share path for smbclient
        share_path = f"//{server}/{share_name}"
        
        # Combine base path from connection, upload_path from config, and filename
        path_parts = []
        if base_path:
            path_parts.append(base_path.strip('/'))
        if upload_path and upload_path.strip() and upload_path.strip() != '.':
            path_parts.append(upload_path.strip('/'))
        path_parts.append(file.name)
        
        target_file = '/'.join(path_parts) if path_parts else file.name
        
        print(f"[SMB] Share path: {share_path}")
        print(f"[SMB] Target file path: {target_file}")
        
        # Create directory if needed (for nested paths)
        commands = []
        if '/' in target_file:
            # Extract directory path
            dir_path = '/'.join(target_file.split('/')[:-1])
            # Try to create directory (ignore errors if it exists)
            commands.append(f'mkdir "{dir_path}"')
        
        # Add upload command
        commands.append(f'put "{file}" "{target_file}"')
        
        # Combine all commands with semicolon
        cmd_string = '; '.join(commands)
        
        # Use smbclient to upload
        cmd = [
            'smbclient', share_path,
            '-U', f"{username}%{password}",
            '-c', cmd_string
        ]
        
        print(f"[SMB] Executing: smbclient {share_path} [credentials] -c '{cmd_string}'")
        
        result = subprocess.run(cmd, capture_output=True, timeout=60, text=True)
        
        print(f"[SMB] Exit code: {result.returncode}")
        if result.stdout:
            print(f"[SMB] stdout: {result.stdout[:300]}")
        if result.stderr:
            print(f"[SMB] stderr: {result.stderr[:300]}")
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            
            # Parse common errors
            if "NT_STATUS_OBJECT_NAME_NOT_FOUND" in error_msg:
                raise Exception(f"SMB upload failed: Directory '{dir_path if '/' in target_file else ''}' not found on share. Create it manually or check path.")
            elif "NT_STATUS_ACCESS_DENIED" in error_msg:
                raise Exception(f"SMB upload failed: Access denied. Check if user '{username}' has write permissions on '{share_path}'.")
            elif "NT_STATUS_LOGON_FAILURE" in error_msg:
                raise Exception(f"SMB upload failed: Authentication failed. Check username and password.")
            else:
                raise Exception(f"SMB upload failed: {error_msg[:200]}")
        
        print(f"[SMB] ✓ Upload successful: {target_file}")
    
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
        from_addr = target.config.get('from', 'scan2target@localhost')
        to_addr = target.config['connection']  # email address
        
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = f"Scan2Target: {file.name}"
        
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
        base_url = target.config.get('connection', '').rstrip('/')
        if not base_url:
            raise Exception("Paperless-ngx URL is not configured")
        
        url = base_url + '/api/documents/post_document/'
        
        # Support both 'api_token' and 'token' field names
        token = target.config.get('api_token') or target.config.get('token', '')
        if not token:
            raise Exception("Paperless-ngx API token is missing")
        
        print(f"[Paperless] Uploading {file.name} to {base_url}")
        print(f"[Paperless] URL: {url}")
        
        headers = {'Authorization': f'Token {token}'}
        
        # Detect MIME type based on file extension
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file.name)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        print(f"[Paperless] MIME type: {mime_type}")
        
        try:
            with open(file, 'rb') as f:
                files = {'document': (file.name, f, mime_type)}
                response = requests.post(url, files=files, headers=headers, timeout=30)
                
                print(f"[Paperless] Response status: {response.status_code}")
                print(f"[Paperless] Response: {response.text[:200]}")
                
                response.raise_for_status()
                print(f"[Paperless] ✓ Upload successful")
        except requests.exceptions.RequestException as e:
            error_msg = f"Paperless-ngx upload failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" - Status: {e.response.status_code}, Response: {e.response.text[:200]}"
            print(f"[Paperless] ✗ {error_msg}")
            raise Exception(error_msg)
    
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
