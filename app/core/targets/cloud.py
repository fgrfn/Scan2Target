"""Cloud storage target handlers."""
from pathlib import Path
import requests
import json


class GoogleDriveHandler:
    """Google Drive upload handler."""
    
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        """
        Upload file to Google Drive.
        
        Config required:
        - access_token: OAuth2 access token
        - folder_id: Target folder ID (optional)
        """
        access_token = config.get('access_token')
        folder_id = config.get('folder_id')
        
        if not access_token:
            raise Exception("Google Drive access_token required")
        
        # Metadata
        metadata = {
            'name': file_path.name,
        }
        if folder_id:
            metadata['parents'] = [folder_id]
        
        # Upload using multipart
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        files = {
            'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
            'file': (file_path.name, open(file_path, 'rb'))
        }
        
        response = requests.post(
            'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
            headers=headers,
            files=files,
            timeout=60
        )
        response.raise_for_status()


class DropboxHandler:
    """Dropbox upload handler."""
    
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        """
        Upload file to Dropbox.
        
        Config required:
        - access_token: OAuth2 access token
        - path: Target path (e.g., /scans)
        """
        access_token = config.get('access_token')
        target_path = config.get('path', '/scans')
        
        if not access_token:
            raise Exception("Dropbox access_token required")
        
        # Full path in Dropbox
        dropbox_path = f"{target_path.rstrip('/')}/{file_path.name}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream',
            'Dropbox-API-Arg': json.dumps({
                'path': dropbox_path,
                'mode': 'add',
                'autorename': True,
                'mute': False
            })
        }
        
        with open(file_path, 'rb') as f:
            response = requests.post(
                'https://content.dropboxapi.com/2/files/upload',
                headers=headers,
                data=f,
                timeout=60
            )
        
        response.raise_for_status()


class OneDriveHandler:
    """OneDrive upload handler."""
    
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        """
        Upload file to OneDrive.
        
        Config required:
        - access_token: OAuth2 access token
        - path: Target path (e.g., /Documents/Scans)
        """
        access_token = config.get('access_token')
        target_path = config.get('path', '/Scans')
        
        if not access_token:
            raise Exception("OneDrive access_token required")
        
        # Upload URL
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:{target_path}/{file_path.name}:/content"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        
        with open(file_path, 'rb') as f:
            response = requests.put(
                url,
                headers=headers,
                data=f,
                timeout=60
            )
        
        response.raise_for_status()


class NextcloudHandler:
    """Nextcloud/ownCloud WebDAV handler."""
    
    @staticmethod
    def upload(file_path: Path, config: dict) -> None:
        """
        Upload file to Nextcloud via WebDAV.
        
        Config required:
        - url: Nextcloud instance URL (e.g., https://cloud.example.com)
        - username: Username
        - password: Password or app password
        - path: Target path (e.g., /Scans)
        """
        url = config.get('url', '').rstrip('/')
        username = config.get('username')
        password = config.get('password')
        target_path = config.get('path', '/Scans')
        
        if not all([url, username, password]):
            raise Exception("Nextcloud url, username, and password required")
        
        # WebDAV URL
        webdav_url = f"{url}/remote.php/dav/files/{username}{target_path}/{file_path.name}"
        
        with open(file_path, 'rb') as f:
            response = requests.put(
                webdav_url,
                auth=(username, password),
                data=f,
                timeout=60
            )
        
        response.raise_for_status()
