"""Authentication dependencies for FastAPI."""
import hmac

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from core.auth.models import User
from core.auth.manager import get_auth_manager
from core.config.settings import get_settings


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from token.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"message": f"Hello {user.username}"}
    """
    auth_manager = get_auth_manager()
    user = auth_manager.verify_token(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin privileges.
    
    Usage:
        @router.delete("/admin/users/{user_id}")
        async def delete_user(user_id: int, admin: User = Depends(get_current_admin_user)):
            ...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    Dependency for optional authentication.
    
    Returns None if no token provided, validates if token is present.
    """
    if not credentials:
        return None

    auth_manager = get_auth_manager()
    return auth_manager.verify_token(credentials.credentials)


async def verify_homeassistant_access(
    x_api_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> None:
    """
    Guard for the Home Assistant endpoints.

    - If SCAN2TARGET_HA_API_KEY is configured, the key must be supplied via
      the X-API-Key header (or as a Bearer token).
    - If no key is configured but SCAN2TARGET_REQUIRE_AUTH is enabled, a
      valid user token is required instead.
    - Otherwise access is open (default for trusted home networks).
    """
    settings = get_settings()

    if settings.ha_api_key:
        provided = x_api_key or (credentials.credentials if credentials else None)
        if provided and hmac.compare_digest(provided, settings.ha_api_key):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key (X-API-Key header)",
        )

    if settings.require_auth:
        token = credentials.credentials if credentials else None
        if token and get_auth_manager().verify_token(token):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
