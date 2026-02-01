"""Device management API routes - scanners only (cleaned version without printer support)."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

from core.devices.repository import DeviceRepository, DeviceRecord
from core.scanning.manager import ScannerManager
from core.database import get_db

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
    
    Uses multiple discovery methods:
    - airscan-discover for eSCL/AirScan network scanners
    - scanimage -L for SANE backends (USB, network SANE, etc.)
    """
    devices = []
    device_repo = DeviceRepository()
    
    # Get already added device URIs
    added_devices = device_repo.list_devices(device_type='scanner', active_only=True)
    added_uris = {dev.uri for dev in added_devices}
    
    print("[DISCOVERY] Starting scanner discovery...")
    
    # Method 1: Use ScannerManager (airscan-discover)
    try:
        scanner_manager = ScannerManager()
        discovered_scanners = scanner_manager.list_devices()
        
        print(f"[DISCOVERY] Found {len(discovered_scanners)} scanners via airscan-discover")
        
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
        print(f"[DISCOVERY] Error with airscan-discover: {e}")
    
    # Method 2: Fallback to scanimage -L for other SANE backends
    try:
        import subprocess
        import re
        
        result = subprocess.run(
            ['scanimage', '-L'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 and result.stdout:
            print(f"[DISCOVERY] scanimage -L output:\n{result.stdout}")
            
            # Parse scanimage -L output
            # Format: "device `pixma:04A91820_247F69' is a CANON Canon PIXMA MG5200 multi-function peripheral"
            for line in result.stdout.split('\n'):
                if 'device' in line.lower() and '`' in line:
                    # Extract device URI
                    match = re.search(r"`([^']+)'", line)
                    if match:
                        scanner_uri = match.group(1)
                        
                        # Skip if already added via airscan-discover
                        if any(d.uri == scanner_uri for d in devices):
                            continue
                        
                        # Extract device description
                        desc_match = re.search(r"is a (.+)", line)
                        scanner_name = desc_match.group(1).strip() if desc_match else scanner_uri
                        
                        # Try to extract make from URI or name
                        parts = scanner_name.split(None, 2)
                        make = parts[0] if len(parts) > 0 else 'Unknown'
                        model = ' '.join(parts[1:]) if len(parts) > 1 else scanner_name
                        
                        # Determine connection type from URI
                        if scanner_uri.startswith('pixma:'):
                            conn_type = 'USB (PIXMA)'
                        elif scanner_uri.startswith('hpaio:'):
                            conn_type = 'USB/Network (HP)'
                        elif scanner_uri.startswith('net:'):
                            conn_type = 'Network (SANE)'
                        elif 'usb' in scanner_uri.lower():
                            conn_type = 'USB'
                        else:
                            conn_type = 'Unknown'
                        
                        devices.append(DiscoveredDevice(
                            uri=scanner_uri,
                            name=scanner_name,
                            make=make,
                            model=model,
                            connection_type=conn_type,
                            device_type='scanner',
                            supported=True,
                            already_added=scanner_uri in added_uris
                        ))
                        
                        print(f"[DISCOVERY] Found via scanimage -L: {scanner_name} ({scanner_uri})")
    except Exception as e:
        print(f"[DISCOVERY] Error with scanimage -L: {e}")
    
    print(f"[DISCOVERY] Total devices found: {len(devices)}")
    
    if not devices:
        print("[DISCOVERY] No scanners found. Possible reasons:")
        print("  - Scanner not turned on or not connected")
        print("  - Scanner not on same network (for network scanners)")
        print("  - Firewall blocking mDNS/scanner traffic")
        print("  - Scanner doesn't support eSCL/AirScan or SANE")
        print("  - Try adding scanner manually with IP address")
    
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
    **Permanently add** a scanner (discovered or manual).
    
    **MANUAL CONFIRMATION REQUIRED:**
    This endpoint must be explicitly called by the user to add a device.
    
    Process:
    1. User clicks "Discover Scanners" OR enters scanner details manually
    2. User reviews the list of discovered scanners
    3. User selects a scanner and clicks "Add Scanner"
    4. This endpoint is called
    5. Scanner is saved to database
    
    Manual addition examples:
    - Network eSCL scanner: uri="airscan:escl:MyScanner:http://192.168.1.100:8080/eSCL/"
    - HP Network scanner: uri="hpaio:/net/HP_LaserJet?ip=192.168.1.100"
    - Any SANE device: uri="<backend>:<device_identifier>"
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


@router.get("/{device_id}/check")
async def check_scanner_online(device_id: str):
    """Check if a scanner is currently online and accessible."""
    device_repo = DeviceRepository()
    device = device_repo.get_device(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
    
    # Try to detect scanner
    try:
        scanner_manager = ScannerManager()
        scanners = scanner_manager.list_devices()
        
        is_online = any(s['id'] == device.uri for s in scanners)
        
        if is_online:
            return {
                "online": True,
                "device_id": device_id,
                "message": "Scanner is online and ready"
            }
        else:
            # Try a test scan command to verify
            import subprocess
            result = subprocess.run(
                ['scanimage', '--device-name', device.uri, '--test'],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "online": True,
                    "device_id": device_id,
                    "message": "Scanner is online (verified by test scan)"
                }
            else:
                return {
                    "online": False,
                    "device_id": device_id,
                    "message": "Scanner is offline or not responding",
                    "suggestion": "Check if scanner is powered on and connected to network"
                }
    except subprocess.TimeoutExpired:
        return {
            "online": False,
            "device_id": device_id,
            "message": "Scanner connection timeout",
            "suggestion": "Check network connection and scanner IP address"
        }
    except Exception as e:
        return {
            "online": False,
            "device_id": device_id,
            "message": f"Error checking scanner: {str(e)}",
            "suggestion": "Verify scanner configuration and network connectivity"
        }
