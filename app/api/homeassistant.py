"""Home Assistant Integration API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import asyncio

from app.core.database import get_db, Database
from app.core.devices.repository import DeviceRepository
from app.core.targets.repository import TargetRepository
from app.core.jobs.repository import JobRepository
from app.core.jobs.manager import JobManager
from app.core.auth.dependencies import get_current_user_optional

router = APIRouter()


class HomeAssistantScanRequest(BaseModel):
    """Home Assistant scan request model."""
    scanner_id: Optional[str] = Field(None, description="Scanner ID or 'favorite' to use favorite scanner")
    target_id: Optional[str] = Field(None, description="Target ID or 'favorite' to use favorite target")
    profile: Optional[str] = Field("document", description="Scan profile name")
    filename: Optional[str] = Field(None, description="Custom filename (without extension)")
    source: Optional[str] = Field("Flatbed", description="Scan source (Flatbed or ADF)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "scanner_id": "favorite",
                "target_id": "favorite",
                "profile": "document",
                "filename": "scan_{date}",
                "source": "Flatbed"
            }
        }


class HomeAssistantScanResponse(BaseModel):
    """Home Assistant scan response model."""
    success: bool
    job_id: str
    message: str
    scanner_name: Optional[str] = None
    target_name: Optional[str] = None
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class HomeAssistantStatusResponse(BaseModel):
    """Home Assistant status response model."""
    online: bool
    scanner_count: int
    target_count: int
    active_scans: int
    last_scan: Optional[datetime] = None
    favorite_scanner: Optional[str] = None
    favorite_target: Optional[str] = None


@router.post("/scan", response_model=HomeAssistantScanResponse)
async def trigger_scan_from_homeassistant(
    request: HomeAssistantScanRequest,
    db: Database = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Trigger a scan from Home Assistant.
    
    This endpoint allows Home Assistant to trigger scans via REST commands or webhooks.
    
    **Usage Examples:**
    
    1. **Quick Scan (using favorites):**
    ```yaml
    rest_command:
      scan_document:
        url: http://YOUR_SERVER_IP/api/v1/homeassistant/scan
        method: POST
        content_type: "application/json"
        payload: '{"scanner_id": "favorite", "target_id": "favorite"}'
    ```
    
    2. **Specific Scanner and Target:**
    ```yaml
    rest_command:
      scan_to_nas:
        url: http://YOUR_SERVER_IP/api/v1/homeassistant/scan
        method: POST
        content_type: "application/json"
        payload: '{"scanner_id": "{{scanner_id}}", "target_id": "{{target_id}}", "profile": "document"}'
    ```
    
    3. **Multi-Page ADF Scan:**
    ```yaml
    rest_command:
      scan_multipage:
        url: http://YOUR_SERVER_IP/api/v1/homeassistant/scan
        method: POST
        content_type: "application/json"
        payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "adf", "source": "ADF"}'
    ```
    """
    device_repo = DeviceRepository(db)
    target_repo = TargetRepository(db)
    job_repo = JobRepository(db)
    job_manager = JobManager()
    
    try:
        # Resolve scanner
        scanner_id = request.scanner_id
        scanner = None
        
        if scanner_id == "favorite" or scanner_id is None:
            # Get favorite scanner from database
            scanners = device_repo.list_devices(device_type="scanner")
            favorite_scanners = [s for s in scanners if s.is_favorite]
            if not favorite_scanners:
                raise HTTPException(
                    status_code=400,
                    detail="No favorite scanner configured. Please mark a scanner as favorite in the Web UI (⭐ star icon)."
                )
            scanner = favorite_scanners[0]
            scanner_id = scanner.id
        else:
            # Get scanner by ID
            scanner = device_repo.get_by_id(scanner_id)
            if not scanner:
                raise HTTPException(
                    status_code=404,
                    detail=f"Scanner not found: {scanner_id}"
                )
        
        # Resolve target
        target_id = request.target_id
        target = None
        
        if target_id == "favorite" or target_id is None:
            # Get favorite target from database
            targets = target_repo.list_targets()
            favorite_targets = [t for t in targets if t.is_favorite]
            if not favorite_targets:
                raise HTTPException(
                    status_code=400,
                    detail="No favorite target configured. Please mark a target as favorite in the Web UI (⭐ star icon)."
                )
            target = favorite_targets[0]
            target_id = target.id
        else:
            # Get target by ID
            target = target_repo.get_by_id(target_id)
            if not target:
                raise HTTPException(
                    status_code=404,
                    detail=f"Target not found: {target_id}"
                )
        
        # Generate filename
        filename = request.filename or f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create job
        job_id = job_repo.create_job(
            scanner_id=scanner_id,
            scanner_name=scanner.name,
            target_id=target_id,
            target_name=target.name,
            profile=request.profile,
            filename=filename,
            source=request.source,
            triggered_by="homeassistant"
        )
        
        # Start scan in background
        asyncio.create_task(
            job_manager.execute_scan(
                job_id=job_id,
                scanner_uri=scanner.uri,
                profile=request.profile,
                target_id=target_id,
                filename=filename,
                source=request.source
            )
        )
        
        # Estimate duration based on profile
        estimated_duration = 15  # Default
        if "photo" in request.profile.lower() or "600" in request.profile:
            estimated_duration = 30
        elif "adf" in request.profile.lower():
            estimated_duration = 45
        
        return HomeAssistantScanResponse(
            success=True,
            job_id=job_id,
            message=f"Scan started successfully",
            scanner_name=scanner.name,
            target_name=target.name,
            estimated_duration=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start scan: {str(e)}"
        )


@router.get("/status", response_model=HomeAssistantStatusResponse)
async def get_homeassistant_status(
    db: Database = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Get Scan2Target status for Home Assistant sensors.
    
    This endpoint provides system status information that can be used in Home Assistant sensors.
    
    **Usage Example:**
    ```yaml
    sensor:
      - platform: rest
        name: "Scan2Target Status"
        resource: http://YOUR_SERVER_IP/api/v1/homeassistant/status
        method: GET
        value_template: "{{ value_json.online }}"
        json_attributes:
          - scanner_count
          - target_count
          - active_scans
          - favorite_scanner
          - favorite_target
        scan_interval: 30
    ```
    """
    device_repo = DeviceRepository(db)
    target_repo = TargetRepository(db)
    job_repo = JobRepository(db)
    
    try:
        # Get counts
        scanners = device_repo.list_devices(device_type="scanner")
        targets = target_repo.list_targets()
        active_jobs = job_repo.get_active_jobs()
        
        # Get last scan
        recent_jobs = job_repo.list_jobs(limit=1, offset=0)
        last_scan = recent_jobs[0].created_at if recent_jobs else None
        
        # Get favorites
        favorite_scanners = [s for s in scanners if s.is_favorite]
        favorite_scanner = favorite_scanners[0] if favorite_scanners else None
        
        favorite_targets = [t for t in targets if t.is_favorite]
        favorite_target = favorite_targets[0] if favorite_targets else None
        
        return HomeAssistantStatusResponse(
            online=True,
            scanner_count=len(scanners),
            target_count=len(targets),
            active_scans=len(active_jobs),
            last_scan=last_scan,
            favorite_scanner=favorite_scanner.name if favorite_scanner else None,
            favorite_target=favorite_target.name if favorite_target else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/scanners")
async def list_scanners_for_homeassistant(
    db: Database = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    List available scanners for Home Assistant dropdown/select.
    
    **Usage Example:**
    ```yaml
    input_select:
      scan_scanner:
        name: Scanner
        options:
          - Fetch from API
    ```
    """
    device_repo = DeviceRepository(db)
    
    try:
        scanners = device_repo.list_devices(device_type="scanner")
        return {
            "scanners": [
                {
                    "id": s.id,
                    "name": s.name,
                    "is_favorite": s.is_favorite
                }
                for s in scanners
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list scanners: {str(e)}"
        )


@router.get("/targets")
async def list_targets_for_homeassistant(
    db: Database = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    List available targets for Home Assistant dropdown/select.
    
    **Usage Example:**
    ```yaml
    input_select:
      scan_target:
        name: Target
        options:
          - Fetch from API
    ```
    """
    target_repo = TargetRepository(db)
    
    try:
        targets = target_repo.list_targets()
        return {
            "targets": [
                {
                    "id": t.id,
                    "name": t.name,
                    "type": t.target_type,
                    "is_favorite": t.is_favorite
                }
                for t in targets
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list targets: {str(e)}"
        )


@router.get("/profiles")
async def list_profiles_for_homeassistant(current_user = Depends(get_current_user_optional)):
    """
    List available scan profiles for Home Assistant dropdown/select.
    """
    return {
        "profiles": [
            {"id": "document", "name": "Document @200 DPI (Gray)"},
            {"id": "adf", "name": "Multi-Page (ADF)"},
            {"id": "color", "name": "Color @300 DPI"},
            {"id": "photo", "name": "Photo @600 DPI"}
        ]
    }
