"""Authentication utilities - JWT, password hashing."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
import hmac
import base64
import json

from app.core.auth.models import User, UserRepository
from app.core.database import get_db


class AuthManager:
    """
    Authentication manager with JWT tokens and password hashing.
    
    Uses HMAC-SHA256 for tokens and bcrypt-style hashing for passwords.
    """
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._generate_secret()
        self.user_repo = UserRepository()
        self.db = get_db()
    
    def _generate_secret(self) -> str:
        """Generate a random secret key."""
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using PBKDF2-SHA256."""
        salt = secrets.token_bytes(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        # Store as salt:hash in base64
        return base64.b64encode(salt).decode() + ':' + base64.b64encode(hash_obj).decode()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt_b64, hash_b64 = password_hash.split(':')
            salt = base64.b64decode(salt_b64)
            expected_hash = base64.b64decode(hash_b64)
            
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return hmac.compare_digest(hash_obj, expected_hash)
        except Exception:
            return False
    
    def create_token(self, user: User, expires_in: int = 3600) -> str:
        """
        Create a JWT-style token for a user.
        
        Args:
            user: User object
            expires_in: Token expiration time in seconds (default 1 hour)
        
        Returns:
            Signed token string
        """
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        payload = {
            'user_id': user.id,
            'username': user.username,
            'is_admin': user.is_admin,
            'exp': expires_at.timestamp()
        }
        
        # Create token: base64(payload) + '.' + signature
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        signature = hmac.new(
            self.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{payload_b64}.{signature}"
        
        # Store token in sessions table
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (token, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (token, user.id, expires_at.isoformat(), datetime.utcnow().isoformat()))
        
        return token
    
    def verify_token(self, token: str) -> Optional[User]:
        """
        Verify and decode a token.
        
        Returns:
            User object if token is valid, None otherwise
        """
        try:
            # Split token
            payload_b64, signature = token.split('.')
            
            # Verify signature
            expected_sig = hmac.new(
                self.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            # Decode payload
            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
            
            # Check expiration
            if datetime.utcnow().timestamp() > payload['exp']:
                return None
            
            # Check if token is revoked
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT revoked FROM sessions WHERE token = ?",
                    (token,)
                )
                row = cursor.fetchone()
                if not row or row['revoked']:
                    return None
            
            # Get user
            user = self.user_repo.get_by_id(payload['user_id'])
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token (logout)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE sessions SET revoked = 1 WHERE token = ?",
                    (token,)
                )
                return cursor.rowcount > 0
        except Exception:
            return False
    
    def login(self, username: str, password: str) -> Optional[tuple[User, str]]:
        """
        Authenticate user and create token.
        
        Returns:
            (User, token) tuple if successful, None otherwise
        """
        result = self.user_repo.get_by_username(username)
        if not result:
            return None
        
        user, password_hash = result
        
        if not user.is_active:
            return None
        
        if not self.verify_password(password, password_hash):
            return None
        
        # Update last login
        self.user_repo.update_last_login(user.id)
        
        # Create token
        token = self.create_token(user)
        
        return user, token
    
    def register(self, username: str, password: str, email: str = None, is_admin: bool = False) -> User:
        """
        Register a new user.
        
        Raises:
            ValueError: If username already exists
        """
        if self.user_repo.user_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        
        password_hash = self.hash_password(password)
        return self.user_repo.create(username, password_hash, email, is_admin)


# Global auth manager instance
_auth_manager = None


def get_auth_manager() -> AuthManager:
    """Get or create the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
