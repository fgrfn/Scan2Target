"""Scan-related API routes."""
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess

from app.core.scanning.manager import ScannerManager
from app.core.jobs.models import JobStatus, JobRecord

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
async def preview_scan(request: dict):
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
    
    device_id = request.get('device_id')
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
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


@router.post("/batch", response_model=ScanJobResponse)
async def start_batch_scan(payload: BatchScanRequest):
    """Combine multiple scanned pages into one PDF and upload to target."""
    from fastapi import HTTPException
    from app.core.devices.repository import DeviceRepository
    from PIL import Image
    import io
    
    # Validate inputs
    if not payload.device_id or payload.device_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a scanner")
    
    if not payload.target_id or payload.target_id.strip() == "":
        raise HTTPException(status_code=400, detail="Please select a target destination")
    
    if not payload.page_urls or len(payload.page_urls) == 0:
        raise HTTPException(status_code=400, detail="No pages in batch")
    
    try:
        # Get device info for job tracking
        device_repo = DeviceRepository()
        device = device_repo.get_device(payload.device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Scanner '{payload.device_id}' not found")
        
        # Create a temporary PDF from all preview images
        from pathlib import Path
        import tempfile
        import uuid
        
        batch_id = str(uuid.uuid4())
        temp_dir = Path(tempfile.gettempdir()) / "scan2target_batch" / batch_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download/collect all page images
            images = []
            for idx, page_url in enumerate(payload.page_urls):
                # page_url is like: /api/v1/scan/preview?image=xxx
                # We need to extract the actual file path from the preview storage
                # For now, we'll use the scanimage approach for each page
                print(f"Processing batch page {idx + 1}/{len(payload.page_urls)}")
                
                # Trigger a real scan for this page
                page_file = temp_dir / f"page_{idx + 1:03d}.jpg"
                
                result = subprocess.run(
                    [
                        'scanimage',
                        '--device-name', device.uri,
                        '--resolution', '300',  # High res for final PDF
                        '--mode', 'Color',
                        '--format', 'jpeg'
                    ],
                    stdout=open(page_file, 'wb'),
                    stderr=subprocess.PIPE,
                    timeout=60
                )
                
                if result.returncode != 0:
                    raise Exception(f"Scan failed for page {idx + 1}: {result.stderr.decode()}")
                
                images.append(Image.open(page_file))
            
            # Convert all images to PDF
            pdf_file = temp_dir / f"{payload.filename_prefix or 'batch_scan'}_{batch_id}.pdf"
            
            if len(images) > 0:
                # Convert all images to RGB (PDF requires RGB)
                rgb_images = [img.convert('RGB') for img in images]
                
                # Save first image as PDF with additional pages
                rgb_images[0].save(
                    pdf_file,
                    save_all=True,
                    append_images=rgb_images[1:] if len(rgb_images) > 1 else [],
                    resolution=300.0,
                    quality=85
                )
                
                print(f"✓ Created PDF with {len(images)} pages: {pdf_file}")
                
                # Now create a job to upload this PDF
                from app.core.jobs.manager import JobManager
                from app.core.jobs.models import JobRecord, JobStatus
                
                job_id = str(uuid.uuid4())
                job = JobRecord(
                    id=job_id,
                    device_id=payload.device_id,
                    target_id=payload.target_id,
                    profile_id=payload.profile_id or "batch_scan",
                    filename=pdf_file.name,
                    status=JobStatus.completed,  # Scan is done
                    file_path=str(pdf_file)
                )
                
                # Add job and trigger upload
                job_manager = JobManager()
                job_manager.create_job(job)
                
                # Enqueue upload task
                from app.core.worker import enqueue_upload
                enqueue_upload(job_id, payload.target_id, str(pdf_file))
                
                return ScanJobResponse(job_id=job_id, status=JobStatus.queued)
            else:
                raise Exception("No images to process")
                
        finally:
            # Cleanup images
            for img in images:
                img.close()
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch scan failed: {str(e)}")
