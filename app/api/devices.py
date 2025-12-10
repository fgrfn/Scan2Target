"""Device management API routes - scanners only (cleaned version without printer support)."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

from app.core.devices.repository import DeviceRepository, DeviceRecord
from app.core.scanning.manager import ScannerManager

router = APIRouter()

# Cache for scanner status (updated every 30 seconds)
_scanner_cache = {
    'devices': [],
    'last_update': 0,
    'cache_duration': 30  # seconds
}


class DiscoveredDevice(BaseModel):
    """Device discovered but not yet added."""
    uri: str
    name: str
    make: str | None = None
    model: str | None = None
    connection_type: str
    device_type: str = 'scanner'
    supported: bool = True
    already_added: bool = False


class AddDeviceRequest(BaseModel):
    """Request to add a scanner."""
    uri: str
    name: str
    device_type: str = 'scanner'
    make: str | None = None
    model: str | None = None
    connection_type: str | None = None
    description: str | None = None


class DeviceResponse(BaseModel):
    """Response for device operations."""
    id: str
    device_type: str
    name: str
    uri: str
    make: str | None
    model: str | None
    connection_type: str | None
    description: str | None
    is_active: bool
    is_favorite: bool = False
    status: str | None = None


@router.get("/discover", response_model=List[DiscoveredDevice])
async def discover_devices():
    """
    Discover available scanners on the network and via USB.
    
    **IMPORTANT: This only discovers devices, does NOT add them!**
    
    Process:
    1. Scans for available scanners (USB, network, eSCL, etc.)
    2. Returns list of discovered devices
    3. Shows which devices are already added (`already_added: true/false`)
    4. User must explicitly call POST /devices/add to add a device
    """
    devices = []
    device_repo = DeviceRepository()
    
    # Get already added device URIs
    added_devices = device_repo.list_devices(device_type='scanner', active_only=True)
    added_uris = {dev.uri for dev in added_devices}
    
    # Discover scanners via SANE
    try:
        scanner_manager = ScannerManager()
        discovered_scanners = scanner_manager.list_devices()
        
        for scanner in discovered_scanners:
            scanner_uri = scanner['id']
            conn_type = scanner.get('type', 'Unknown')
            
            # Extract make/model from name if possible
            scanner_name = scanner.get('name', 'Unknown Scanner')
            parts = scanner_name.split(None, 2)
            make = parts[0] if len(parts) > 0 else 'Unknown'
            model = ' '.join(parts[1:]) if len(parts) > 1 else scanner_name
            
            devices.append(DiscoveredDevice(
                uri=scanner_uri,
                name=scanner_name,
                make=make,
                model=model,
                connection_type=conn_type,
                device_type='scanner',
                supported=scanner.get('supported', True),
                already_added=scanner_uri in added_uris
            ))
    except Exception as e:
        print(f"Error discovering scanners: {e}")
    
    return devices


def _update_scanner_cache():
    """Update cached scanner list if expired."""
    current_time = time.time()
    if current_time - _scanner_cache['last_update'] > _scanner_cache['cache_duration']:
        try:
            scanner_manager = ScannerManager()
            _scanner_cache['devices'] = scanner_manager.list_devices()
            _scanner_cache['last_update'] = current_time
            print(f"[CACHE] Scanner status cache updated")
        except Exception as e:
            print(f"[CACHE] Failed to update scanner cache: {e}")


@router.get("", response_model=List[DeviceResponse])
@router.get("/", response_model=List[DeviceResponse])
async def list_devices(device_type: str | None = None):
    """
    List all permanently added scanners.
    
    **Only shows devices that were explicitly added via POST /devices/add**
    
    Query params:
    - device_type: Filter by 'scanner' (optional, for API compatibility)
    
    Scanner status is cached for 30 seconds for performance.
    """
    start = time.time()
    
    device_repo = DeviceRepository()
    devices = device_repo.list_devices(device_type='scanner', active_only=True)
    
    # Update scanner cache if needed
    _update_scanner_cache()
    
    print(f"[TIMING] list_devices: DB query took {time.time() - start:.3f}s")
    
    response = []
    for device in devices:
        status = "unknown"
        
        # Check status from cache
        cached_scanners = _scanner_cache.get('devices', [])
        if any(s['id'] == device.uri for s in cached_scanners):
            status = "online"
        else:
            status = "offline"
        
        response.append(DeviceResponse(
            id=device.id,
            device_type=device.device_type,
            name=device.name,
            uri=device.uri,
            make=device.make,
            model=device.model,
            connection_type=device.connection_type,
            description=device.description,
            is_active=device.is_active,
            is_favorite=device.is_favorite,
            status=status
        ))
    
    return response


@router.post("/add", response_model=DeviceResponse)
async def add_device(request: AddDeviceRequest):
    """
    **Permanently add** a discovered scanner.
    
    **MANUAL CONFIRMATION REQUIRED:**
    This endpoint must be explicitly called by the user to add a device.
    
    Process:
    1. User clicks "Discover Scanners"
    2. User reviews the list of discovered scanners
    3. User selects a scanner and clicks "Add Scanner"
    4. This endpoint is called
    5. Scanner is saved to database
    """
    device_repo = DeviceRepository()
    
    # Check if device already exists
    if device_repo.device_exists(request.uri):
        raise HTTPException(
            status_code=400,
            detail=f"Scanner with URI '{request.uri}' is already added"
        )
    
    # Generate device ID (sanitized name)
    import re
    device_id = re.sub(r'[^a-zA-Z0-9_-]', '_', request.name.replace(' ', '_'))
    
    # Add to database
    device = DeviceRecord(
        id=device_id,
        device_type='scanner',
        name=request.name,
        uri=request.uri,
        make=request.make,
        model=request.model,
        connection_type=request.connection_type,
        description=request.description,
        is_active=True
    )
    
    try:
        device_repo.add_device(device)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save scanner to database: {str(e)}"
        )
    
    return DeviceResponse(
        id=device.id,
        device_type=device.device_type,
        name=device.name,
        uri=device.uri,
        make=device.make,
        model=device.model,
        connection_type=device.connection_type,
        description=device.description,
        is_active=device.is_active,
        is_favorite=device.is_favorite,
        status="added"
    )


@router.delete("/{device_id}")
async def remove_device(device_id: str):
    """
    **Permanently remove** a scanner.
    
    Removes scanner from database. Any pending jobs for this device may fail.
    """
    device_repo = DeviceRepository()
    
    # Get device info
    device = device_repo.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    
    # Remove from database
    success = device_repo.remove_device(device_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    
    return {
        "status": "removed",
        "device_id": device_id,
        "device_type": device.device_type
    }


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """Get details of a specific scanner."""
    device_repo = DeviceRepository()
    device = device_repo.get_device(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    
    # Check online status
    status = "unknown"
    try:
        scanner_manager = ScannerManager()
        scanners = scanner_manager.list_devices()
        status = "online" if any(s['id'] == device.uri for s in scanners) else "offline"
    except:
        status = "unknown"
    
    return DeviceResponse(
        id=device.id,
        device_type=device.device_type,
        name=device.name,
        uri=device.uri,
        make=device.make,
        model=device.model,
        connection_type=device.connection_type,
        description=device.description,
        is_active=device.is_active,
        is_favorite=device.is_favorite,
        status=status
    )


class ToggleFavoriteRequest(BaseModel):
    is_favorite: bool


@router.post("/{device_id}/favorite")
async def toggle_device_favorite(device_id: str, request: ToggleFavoriteRequest):
    """Toggle favorite status for a scanner."""
    device_repo = DeviceRepository()
    
    # Get device
    device = device_repo.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    
    # Update favorite status
    device.is_favorite = request.is_favorite
    
    # Update in database
    from app.core.database import get_db
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE devices 
            SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if request.is_favorite else 0, device_id))
    
    return {
        "status": "updated",
        "device_id": device_id,
        "is_favorite": request.is_favorite
    }
