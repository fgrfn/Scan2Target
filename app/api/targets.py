"""Target configuration API routes."""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.targets.manager import TargetManager

router = APIRouter()


class Target(BaseModel):
    id: str
    type: str
    name: str
    config: dict
    enabled: bool = True


@router.get("/", response_model=List[Target])
async def list_targets():
    return TargetManager().list_targets()


@router.post("/", response_model=Target)
async def create_target(target: Target):
    return TargetManager().create_target(target)


@router.put("/{target_id}", response_model=Target)
async def update_target(target_id: str, target: Target):
    return TargetManager().update_target(target_id, target)


@router.delete("/{target_id}")
async def delete_target(target_id: str):
    TargetManager().delete_target(target_id)
    return {"status": "deleted"}


@router.post("/{target_id}/test")
async def test_target(target_id: str):
    return TargetManager().test_target(target_id)
