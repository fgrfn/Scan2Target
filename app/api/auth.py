"""Authentication and first-run setup routes."""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from core.auth.dependencies import get_current_admin_user, get_current_user
from core.auth.manager import get_auth_manager
from core.auth.models import User
from core.config.runtime import get_runtime_config

router = APIRouter()
security = HTTPBearer()
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_MAX_FAILURES = 5
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)
    email: str | None = Field(default=None, max_length=254)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_admin: bool


class SetupStatusResponse(BaseModel):
    setup_required: bool


class AuthConfigResponse(BaseModel):
    enabled: bool
    setup_required: bool


class AuthConfigUpdate(BaseModel):
    enabled: bool


class AccountUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    username: str = Field(min_length=3, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    new_password: str | None = Field(default=None, min_length=12, max_length=256)


def _validate_new_credentials(payload: RegisterRequest) -> None:
    if not _USERNAME_RE.fullmatch(payload.username):
        raise HTTPException(
            status_code=422,
            detail="Username may contain letters, numbers, '.', '_' and '-' only",
        )
    password = payload.password
    if not (
        re.search(r"[a-z]", password)
        and re.search(r"[A-Z]", password)
        and re.search(r"\d", password)
    ):
        raise HTTPException(
            status_code=422,
            detail="Password must contain an uppercase letter, lowercase letter and number",
        )


def _rate_limit_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{username.lower()}"


def _check_login_rate_limit(key: str) -> None:
    now = time.monotonic()
    attempts = _login_failures[key]
    while attempts and now - attempts[0] > _LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _LOGIN_MAX_FAILURES:
        retry_after = max(1, int(_LOGIN_WINDOW_SECONDS - (now - attempts[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def _token_response(user: User, token: str) -> TokenResponse:
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    )


@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status():
    """Report whether a fresh installation needs its first administrator."""
    return SetupStatusResponse(setup_required=get_auth_manager().setup_required())


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config():
    return AuthConfigResponse(
        enabled=get_runtime_config().auth_enabled,
        setup_required=get_auth_manager().setup_required(),
    )


@router.put("/config", response_model=AuthConfigResponse)
async def update_auth_config(
    payload: AuthConfigUpdate,
    _admin: User = Depends(get_current_admin_user),
):
    get_runtime_config().set_auth_enabled(payload.enabled)
    return AuthConfigResponse(
        enabled=get_runtime_config().auth_enabled,
        setup_required=get_auth_manager().setup_required(),
    )


@router.patch("/account", response_model=TokenResponse)
async def update_account(
    payload: AccountUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
):
    candidate = RegisterRequest(
        username=payload.username,
        password=payload.new_password or payload.current_password,
        email=payload.email,
    )
    if payload.new_password:
        _validate_new_credentials(candidate)
    elif not _USERNAME_RE.fullmatch(payload.username):
        raise HTTPException(status_code=422, detail="Invalid username")
    try:
        user, token = get_auth_manager().update_account(
            current_user,
            payload.current_password,
            payload.username,
            payload.email,
            payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _token_response(user, token)


@router.post("/setup", response_model=TokenResponse, status_code=201)
async def setup(payload: RegisterRequest):
    """Create the first administrator exactly once and sign it in."""
    auth_manager = get_auth_manager()
    if not auth_manager.setup_required():
        raise HTTPException(status_code=409, detail="Initial setup is already complete")
    _validate_new_credentials(payload)
    try:
        user = auth_manager.register(
            username=payload.username,
            password=payload.password,
            email=payload.email,
            is_admin=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _token_response(user, auth_manager.create_token(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
    """Authenticate a configured user with basic brute-force throttling."""
    auth_manager = get_auth_manager()
    if auth_manager.setup_required():
        raise HTTPException(status_code=428, detail="Initial setup is required")

    key = _rate_limit_key(request, payload.username)
    _check_login_rate_limit(key)
    result = auth_manager.login(payload.username, payload.password)
    if not result:
        _login_failures[key].append(time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _login_failures.pop(key, None)
    user, token = result
    return _token_response(user, token)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    _admin: User = Depends(get_current_admin_user),
):
    """Create an additional non-admin user; administrators only."""
    _validate_new_credentials(payload)
    try:
        user = get_auth_manager().register(
            username=payload.username,
            password=payload.password,
            email=payload.email,
        )
        return UserResponse(**user.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Revoke the current session token."""
    if not get_auth_manager().revoke_token(credentials.credentials):
        raise HTTPException(status_code=400, detail="Token not found or already revoked")
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Return current authenticated user information."""
    return UserResponse(**current_user.model_dump())
