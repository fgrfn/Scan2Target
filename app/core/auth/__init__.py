"""Authentication module."""
from core.auth.manager import AuthManager, get_auth_manager
from core.auth.models import User, UserRepository
from core.auth.dependencies import get_current_user, get_current_admin_user

__all__ = [
    "AuthManager",
    "get_auth_manager",
    "User",
    "UserRepository",
    "get_current_user",
    "get_current_admin_user",
]
