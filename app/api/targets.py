"""Target configuration routes."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

from app.core.targets.manager import TargetManager
from app.core.targets.models import TargetConfig

router = APIRouter()


class Target(BaseModel):
    id: str
    type: str
    name: str
    config: dict
    enabled: bool = True
    description: str | None = None
    is_favorite: bool = False


@router.get("", response_model=List[Target])
@router.get("/", response_model=List[Target])
async def list_targets():
    """List all configured targets."""
    start = time.time()
    try:
        targets = TargetManager().list_targets()
        print(f"[TIMING] list_targets: took {time.time() - start:.3f}s")
        return [
            Target(
                id=t.id,
                type=t.type,
                name=t.name,
                config=t.config,
                enabled=t.enabled,
                description=t.description,
                is_favorite=t.is_favorite
            )
            for t in targets
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list targets: {str(e)}")


@router.post("", response_model=Target)
@router.post("/", response_model=Target)
async def create_target(target: Target, validate: bool = True):
    """
    Create a new target configuration.
    
    **Connection is automatically tested before saving!**
    
    Query params:
    - validate: Test connection before saving (default: true)
    
    If validation fails, target will NOT be saved and error is returned.
    Set validate=false to skip connection test (not recommended).
    """
    try:
        print(f"Creating target: {target.name} (type: {target.type})")
        print(f"Config: {target.config}")
        print(f"Validate: {validate}")
        
        # Convert Pydantic model to TargetConfig
        target_config = TargetConfig(
            id=target.id,
            type=target.type,
            name=target.name,
            config=target.config,
            enabled=target.enabled,
            description=target.description,
            is_favorite=target.is_favorite
        )
        
        result = TargetManager().create_target(target_config, validate=validate)
        
        print(f"✓ Target '{target.name}' created successfully")
        
        return Target(
            id=result.id,
            type=result.type,
            name=result.name,
            config=result.config,
            enabled=result.enabled,
            description=result.description,
            is_favorite=result.is_favorite
        )
    except Exception as e:
        print(f"ERROR creating target: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{target_id}", response_model=Target)
async def update_target(target_id: str, target: Target, validate: bool = True):
    """
    Update an existing target configuration.
    
    **Connection is automatically tested before updating!**
    
    Query params:
    - validate: Test connection before saving (default: true)
    
    If validation fails, target will NOT be updated and error is returned.
    """
    try:
        # Convert Pydantic model to TargetConfig
        target_config = TargetConfig(
            id=target_id,  # Use target_id from path
            type=target.type,
            name=target.name,
            config=target.config,
            enabled=target.enabled,
            description=target.description,
            is_favorite=target.is_favorite
        )
        
        result = TargetManager().update_target(target_id, target_config, validate=validate)
        
        return Target(
            id=result.id,
            type=result.type,
            name=result.name,
            config=result.config,
            enabled=result.enabled,
            description=result.description,
            is_favorite=result.is_favorite
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{target_id}")
async def delete_target(target_id: str):
    """Delete a target configuration."""
    try:
        TargetManager().delete_target(target_id)
        return {"status": "deleted", "target_id": target_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete target: {str(e)}")


@router.post("/{target_id}/test")
async def test_target(target_id: str):
    """Test connectivity to a target."""
    try:
        result = TargetManager().test_target(target_id)
        # If the result has an error status, return 400 with the message
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Connection test failed"))
        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Catch any unexpected errors
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
