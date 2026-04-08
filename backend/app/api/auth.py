from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import app.auth.service as svc
from app.auth.dependencies import get_current_user, require_admin
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    result = svc.login(req.username, req.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user, token = result
    return TokenResponse(access_token=token, user=UserOut(**user))


@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, _=Depends(require_admin)):
    if svc.user_exists(req.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = svc.create_user(req.username, req.password, req.email, is_admin=False)
    return UserOut(**user)


@router.post("/logout")
def logout(creds: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    if creds:
        svc.revoke_token(creds.credentials)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return UserOut(**user)
