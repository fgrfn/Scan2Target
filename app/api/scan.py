"""Scan-related API routes."""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.scanning.manager import ScannerManager
from app.core.jobs.models import JobStatus, JobRecord

router = APIRouter()


class ScanRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str | None = None
    webhook_url: str | None = None


class ScanProfile(BaseModel):
    id: str
    name: str
    dpi: int
    color_mode: str
    paper_size: str
    format: str
    quality: int
    source: str
    batch_scan: bool
    auto_detect: bool
    description: str


class ScanJobResponse(BaseModel):
    job_id: str
    status: JobStatus


@router.get("/devices", response_model=List[dict])
async def list_devices():
    """Return available scanners and capabilities."""
    return ScannerManager().list_devices()


@router.get("/profiles", response_model=List[ScanProfile])
async def list_profiles():
    """Return configured scan profiles."""
    return ScannerManager().list_profiles()


@router.post("/start", response_model=ScanJobResponse)
async def start_scan(payload: ScanRequest):
    """Trigger a scan and enqueue delivery to the selected target."""
    from fastapi import HTTPException
    from app.core.devices.repository import DeviceRepository
    
    # Validate inputs
    if not payload.device_id or payload.device_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scanner")
    
    if not payload.profile_id or payload.profile_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scan profile")
    
    if not payload.target_id or payload.target_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a target destination")
    
    try:
        # Convert device_id to device URI
        # The frontend sends the database ID, but scanimage needs the actual URI
        device_repo = DeviceRepository()
        device = device_repo.get_device(payload.device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Scanner '{payload.device_id}' not found in database")
        
        if device.device_type != 'scanner':
            raise HTTPException(status_code=400, detail=f"Device '{payload.device_id}' is not a scanner")
        
        # Use the device URI for scanning
        device_uri = device.uri
        print(f"Starting scan with device ID: {payload.device_id} -> URI: {device_uri}")
        
        job_id = ScannerManager().start_scan(
            device_id=device_uri,  # Pass URI instead of database ID
            profile_id=payload.profile_id,
            target_id=payload.target_id,
            filename_prefix=payload.filename_prefix,
            webhook_url=payload.webhook_url,
        )
        return ScanJobResponse(job_id=job_id, status=JobStatus.queued)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.get("/jobs", response_model=List[JobRecord])
async def list_scan_jobs():
    """Return recent scan jobs."""
    return ScannerManager().list_jobs()


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_scan_job(job_id: str):
    """Return a single scan job status."""
    return ScannerManager().get_job(job_id)


@router.post("/preview")
async def preview_scan(device_id: str):
    """
    Quick preview scan at low resolution.
    Returns base64 encoded image for immediate display.
    """
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from app.core.devices.repository import DeviceRepository
    import subprocess
    import tempfile
    from pathlib import Path
    import base64
    
    try:
        # Convert device_id to device URI
        device_repo = DeviceRepository()
        device = device_repo.get_device(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
        
        device_uri = device.uri
        
        # Create temp file for preview
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            preview_file = Path(tmp.name)
        
        try:
            # Low-res preview scan (100 DPI, grayscale, JPEG)
            result = subprocess.run(
                [
                    'scanimage',
                    '--device-name', device_uri,
                    '--resolution', '100',
                    '--mode', 'Gray',
                    '--format', 'jpeg'
                ],
                stdout=open(preview_file, 'wb'),
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"scanimage failed: {result.stderr.decode()}")
            
            # Read and encode as base64
            with open(preview_file, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            return JSONResponse({
                "status": "success",
                "image": f"data:image/jpeg;base64,{image_data}",
                "format": "jpeg"
            })
            
        finally:
            # Cleanup
            if preview_file.exists():
                preview_file.unlink()
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Preview scan timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
