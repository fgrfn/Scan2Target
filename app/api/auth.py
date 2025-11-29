"""Authentication routes."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    # TODO: validate user credentials, issue JWT/session token
    return TokenResponse(access_token="stub-token")


@router.post("/logout")
async def logout():
    # TODO: revoke session or add token to blocklist
    return {"status": "logged_out"}
