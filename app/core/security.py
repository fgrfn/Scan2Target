"""Security utilities for encrypting sensitive data."""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import os
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


class SecureStorage:
    """Encrypts and decrypts sensitive configuration data."""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """
        Get or create encryption key.
        
        The key is derived from:
        1. Environment variable SCAN2TARGET_SECRET_KEY (if set)
        2. Or a machine-specific file in the app directory
        
        This ensures:
        - Production: Use env var for security
        - Development: Auto-generated, persisted key
        """
        # Try environment variable first (production)
        env_secret = os.getenv('SCAN2TARGET_SECRET_KEY')
        if env_secret:
            # Derive key from secret using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'scan2target_salt_v1',  # Static salt for consistency
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(env_secret.encode()))
            return key
        
        # Fall back to file-based key (development)
        key_file = Path.home() / '.scan2target' / 'encryption.key'
        
        if key_file.exists():
            return key_file.read_bytes()
        
        # Generate new key
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Owner read/write only
        
        logger.warning(f"[SECURITY] Generated new encryption key: {key_file}")
        logger.warning("[SECURITY] For production, set SCAN2TARGET_SECRET_KEY environment variable")
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext and return plaintext."""
        if not ciphertext:
            return ""
        
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"[SECURITY] Decryption failed: {e}")
            # Return empty string instead of crashing
            # This handles cases where data wasn't encrypted yet
            return ""
    
    def encrypt_config(self, config: dict) -> dict:
        """
        Encrypt sensitive fields in a config dictionary.
        
        Encrypts: password, api_token, access_token, smtp credentials
        """
        encrypted_config = config.copy()
        
        sensitive_fields = [
            'password',
            'api_token',
            'access_token',
            'refresh_token'
        ]
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                encrypted_config[field] = self.encrypt(encrypted_config[field])
        
        return encrypted_config
    
    def decrypt_config(self, config: dict) -> dict:
        """
        Decrypt sensitive fields in a config dictionary.
        
        Returns config with decrypted sensitive fields.
        """
        decrypted_config = config.copy()
        
        sensitive_fields = [
            'password',
            'api_token',
            'access_token',
            'refresh_token'
        ]
        
        for field in sensitive_fields:
            if field in decrypted_config and decrypted_config[field]:
                decrypted = self.decrypt(decrypted_config[field])
                # Only use decrypted value if it's not empty
                # This handles migration from unencrypted data
                if decrypted:
                    decrypted_config[field] = decrypted
        
        return decrypted_config


# Global instance
_secure_storage = None


def get_secure_storage() -> SecureStorage:
    """Get or create the global SecureStorage instance."""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage
