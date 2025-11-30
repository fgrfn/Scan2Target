"""Authentication routes."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.auth.manager import get_auth_manager
from app.core.auth.models import User
from app.core.auth.dependencies import get_current_user

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_admin: bool


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    Returns:
        Token and user information
    """
    auth_manager = get_auth_manager()
    result = auth_manager.login(payload.username, payload.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, token = result
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    )


@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest):
    """
    Register a new user.
    
    Note: In production, you may want to restrict registration or require admin approval.
    """
    auth_manager = get_auth_manager()
    
    try:
        user = auth_manager.register(
            username=payload.username,
            password=payload.password,
            email=payload.email
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user by revoking token.
    """
    auth_manager = get_auth_manager()
    token = credentials.credentials
    
    success = auth_manager.revoke_token(token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token not found or already revoked"
        )
    
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin
    )
