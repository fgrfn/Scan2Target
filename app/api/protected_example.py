"""Example of protected API routes using authentication."""
from fastapi import APIRouter, Depends

from core.auth.dependencies import get_current_user, get_current_admin_user
from core.auth.models import User

router = APIRouter()


@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """
    Example of a protected route requiring authentication.
    
    To use this route:
    1. Login to get a token: POST /api/v1/auth/login
    2. Include token in header: Authorization: Bearer YOUR_TOKEN
    """
    return {
        "message": f"Hello {current_user.username}!",
        "user_id": current_user.id,
        "is_admin": current_user.is_admin
    }


@router.get("/admin-only")
async def admin_only_route(admin_user: User = Depends(get_current_admin_user)):
    """
    Example of an admin-only route.
    
    Requires authentication AND admin privileges.
    """
    return {
        "message": f"Welcome admin {admin_user.username}!",
        "admin_panel": "access_granted"
    }


# Example: How to protect existing routes
# 
# For scan routes:
# @router.post("/start", response_model=ScanJobResponse)
# async def start_scan(
#     payload: ScanRequest,
#     current_user: User = Depends(get_current_user)  # Add this line
# ):
#     ...
#
# For admin-only printer configuration:
# @router.post("/add")
# async def add_printer(
#     printer: AddPrinterRequest,
#     admin_user: User = Depends(get_current_admin_user)  # Require admin
# ):
#     ...
