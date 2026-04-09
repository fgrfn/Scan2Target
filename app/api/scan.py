"""Scan-related API routes."""
import logging
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import base64

from core.scanning.manager import ScannerManager

logger = logging.getLogger(__name__)
from core.jobs.models import JobStatus, JobRecord

router = APIRouter()


class ScanRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str | None = None
    webhook_url: str | None = None


class BatchScanRequest(BaseModel):
    device_id: str
    profile_id: str
    target_id: str
    filename_prefix: str | None = None
    page_urls: List[str]  # List of preview URLs to combine


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
    from core.devices.repository import DeviceRepository
    
    # Validate inputs
    if not payload.device_id or payload.device_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scanner")
    
    if not payload.profile_id or payload.profile_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scan profile")
    
    if not payload.target_id or payload.target_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a target destination")
    
    delivered = False
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
        logger.info(f"Starting scan with device ID: {payload.device_id} -> URI: {device_uri}")
        
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
        logger.error(f"Scan error: {e}")
        error_msg = str(e)
        
        # Add helpful suggestions based on error type
        if 'device not found' in error_msg.lower():
            error_msg += " | Suggestion: Check if scanner is powered on and connected"
        elif 'timeout' in error_msg.lower():
            error_msg += " | Suggestion: Scanner may be busy or not responding. Wait and try again"
        elif 'permission denied' in error_msg.lower():
            error_msg += " | Suggestion: Scanner access permissions issue. Check scanner configuration"
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/jobs", response_model=List[JobRecord])
async def list_scan_jobs():
    """Return recent scan jobs."""
    return ScannerManager().list_jobs()


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_scan_job(job_id: str):
    """Return a single scan job status."""
    return ScannerManager().get_job(job_id)


@router.post("/jobs/{job_id}/cancel")
async def cancel_scan_job(job_id: str):
    """Cancel a running or queued scan job."""
    from fastapi import HTTPException
    from core.jobs.manager import JobManager
    
    job_manager = JobManager()
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job not found or cannot be cancelled (already completed/failed)"
        )
    
    return {
        "status": "cancelled",
        "job_id": job_id,
        "message": "Scan job has been cancelled"
    }


@router.get("/jobs/{job_id}/thumbnail")
async def get_job_thumbnail(job_id: str):
    """Get thumbnail preview for a completed scan job."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from core.jobs.manager import JobManager
    from pathlib import Path
    
    job_manager = JobManager()
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.thumbnail_path:
        thumbnail = Path(job.thumbnail_path)
        if thumbnail.exists():
            return FileResponse(thumbnail, media_type="image/jpeg")
    
    raise HTTPException(status_code=404, detail="Thumbnail not available")


@router.post("/preview")
async def preview_scan(request: dict):
    """
    Quick preview scan at low resolution.
    Returns base64 encoded image for immediate display.
    """
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from core.devices.repository import DeviceRepository
    import tempfile
    from pathlib import Path
    
    device_id = request.get('device_id')
    profile_id = request.get('profile_id')
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    preview_file = None
    try:
        # Convert device_id to device URI
        device_repo = DeviceRepository()
        device = device_repo.get_device(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Scanner '{device_id}' not found")
        
        device_uri = device.uri
        
        # Get profile settings
        scanner_mgr = ScannerManager()
        profiles = scanner_mgr.list_profiles()
        profile = next((p for p in profiles if p['id'] == profile_id), None)
        
        # Use profile settings or defaults
        color_mode = profile['color_mode'] if profile else 'Gray'
        dpi = min(profile['dpi'] if profile else 150, 200)  # Cap preview at 200 DPI for speed
        
        # Create temp file for preview
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            preview_file = Path(tmp.name)
        
        # Preview scan with profile settings
        cmd = [
            'scanimage',
            '--device-name', device_uri,
            '--resolution', str(dpi),
            '--mode', color_mode,
            '--format', 'jpeg'
        ]
        with open(preview_file, 'wb') as output:
            result = subprocess.run(
                cmd,
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=30
            )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            raise Exception(f"scanimage failed: {error_msg}")
        
        with open(preview_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        return JSONResponse({
            "status": "success",
            "image": f"data:image/jpeg;base64,{image_data}",
            "format": "jpeg"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview scan failed: {str(e)}")
    finally:
        try:
            if preview_file and preview_file.exists():
                preview_file.unlink()
        except Exception:
            pass
@router.post("/batch", response_model=ScanJobResponse)
async def start_batch_scan(payload: BatchScanRequest):
    """Combine multiple scanned pages into one PDF and upload to target."""
    from fastapi import HTTPException
    from core.devices.repository import DeviceRepository
    from core.jobs.manager import JobManager
    from core.jobs.models import JobStatus
    from core.targets.manager import TargetManager
    from PIL import Image
    from pathlib import Path
    import tempfile
    import uuid
    
    # Validate inputs
    if not payload.device_id or payload.device_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scanner")
    
    if not payload.target_id or payload.target_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a target destination")
    
    if not payload.page_urls or len(payload.page_urls) == 0:
        raise HTTPException(status_code=400, detail="No pages in batch")
    
    batch_id = str(uuid.uuid4())
    temp_dir = Path(tempfile.gettempdir()) / "scan2target_batch" / batch_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = temp_dir / f"{payload.filename_prefix or 'batch_scan'}_{batch_id}.pdf"
    
    delivered = False
    try:
        # Get device info for job tracking
        device_repo = DeviceRepository()
        device = device_repo.get_device(payload.device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Scanner '{payload.device_id}' not found")
        
        # Get profile settings
        scanner_mgr = ScannerManager()
        profiles = scanner_mgr.list_profiles()
        profile = next((p for p in profiles if p['id'] == payload.profile_id), None)
        
        if not profile:
            raise HTTPException(status_code=400, detail=f"Profile '{payload.profile_id}' not found")
        
        # Decode all page images from base64
        images = []
        for idx, page_url in enumerate(payload.page_urls):
            logger.debug(f"Processing batch page {idx + 1}/{len(payload.page_urls)}")
            if page_url.startswith('data:image'):
                base64_data = page_url.split(',', 1)[1]
                image_data = base64.b64decode(base64_data)
                from io import BytesIO
                images.append(Image.open(BytesIO(image_data)))
            else:
                raise Exception(f"Invalid page URL format for page {idx + 1}")
        
        if not images:
            raise Exception("No images to process")
        
        rgb_images = [img.convert('RGB') for img in images]
        quality = profile.get('quality', 85)
        dpi = profile.get('dpi', 200)
        rgb_images[0].save(
            pdf_file,
            save_all=True,
            append_images=rgb_images[1:] if len(rgb_images) > 1 else [],
            resolution=float(dpi),
            quality=quality
        )
        logger.info(f"✓ Created PDF with {len(images)} pages: {pdf_file}")
        
        job_id = str(uuid.uuid4())
        job_manager = JobManager()
        job_manager.create_job(
            job_id=job_id,
            job_type="scan",
            device_id=payload.device_id,
            target_id=payload.target_id,
            status=JobStatus.running,
        )
        
        job = job_manager.get_job(job_id)
        if job:
            job.file_path = str(pdf_file)
            job_manager.update_job(job)
        
        TargetManager().deliver(payload.target_id, str(pdf_file), {'job_id': job_id})
        delivered = True
        
        job = job_manager.get_job(job_id)
        if job:
            job.status = JobStatus.completed
            job.message = None
            job_manager.update_job(job)
        
        return ScanJobResponse(job_id=job_id, status=JobStatus.completed)
    except HTTPException:
        raise
    except Exception as e:
        # Update job status if it exists
        try:
            job_manager = JobManager()
            job = job_manager.get_job(job_id) if 'job_id' in locals() else None
            if job:
                job.status = JobStatus.failed
                job.message = str(e)
                job_manager.update_job(job)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Batch scan failed: {str(e)}")
    finally:
        try:
            if delivered and pdf_file.exists():
                pdf_file.unlink()
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except Exception:
            pass
    
