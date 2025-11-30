"""User models and repository."""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db


class User(BaseModel):
    """User model."""
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserRepository:
    """Repository for user persistence."""
    
    def __init__(self):
        self.db = get_db()
    
    def create(self, username: str, password_hash: str, email: str = None, is_admin: bool = False) -> User:
        """Create a new user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash, email, 1 if is_admin else 0, datetime.utcnow().isoformat()))
            
            user_id = cursor.lastrowid
            
        return User(
            id=user_id,
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=True,
            created_at=datetime.utcnow()
        )
    
    def get_by_username(self, username: str) -> Optional[tuple[User, str]]:
        """Get user and password hash by username."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row:
                user = User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    is_active=bool(row['is_active']),
                    is_admin=bool(row['is_admin']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
                )
                return user, row['password_hash']
        return None
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    is_active=bool(row['is_active']),
                    is_admin=bool(row['is_admin']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
                )
        return None
    
    def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user_id)
            )
    
    def user_exists(self, username: str) -> bool:
        """Check if username exists."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row['count'] > 0
