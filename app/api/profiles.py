"""Scan profile management API routes."""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.scanning.profiles import get_profile_repository

logger = logging.getLogger(__name__)

router = APIRouter()


class ProfilePayload(BaseModel):
    id: Optional[str] = Field(None, description="Profile ID (required on create)")
    name: str
    dpi: int = Field(ge=50, le=1200)
    color_mode: str = Field(pattern="^(Color|Gray|Lineart)$")
    paper_size: str = "A4"
    format: str = Field(pattern="^(pdf|jpeg)$")
    quality: int = Field(85, ge=10, le=100)
    source: str = Field("Flatbed", pattern="^(Flatbed|ADF)$")
    batch_scan: bool = False
    auto_detect: bool = True
    description: str = ""


class ProfileResponse(ProfilePayload):
    id: str
    is_builtin: bool = False


@router.get("/", response_model=List[ProfileResponse])
async def list_profiles():
    """Return all scan profiles."""
    return get_profile_repository().list()


@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(payload: ProfilePayload):
    """Create a custom scan profile."""
    if not payload.id:
        raise HTTPException(status_code=400, detail="Profile ID is required")
    try:
        return get_profile_repository().create(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, payload: ProfilePayload):
    """Update an existing scan profile."""
    try:
        return get_profile_repository().update(profile_id, payload.model_dump(exclude={"id"}))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a custom scan profile (built-ins cannot be deleted)."""
    try:
        deleted = get_profile_repository().delete(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return {"status": "deleted", "id": profile_id}
