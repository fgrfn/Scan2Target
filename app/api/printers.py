"""Printer-related API routes."""
from typing import List
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from app.core.printing.manager import PrinterManager
from app.core.jobs.models import JobRecord

router = APIRouter()


class PrintJobRequest(BaseModel):
    printer_id: str
    options: dict | None = None


class PrintJobResponse(BaseModel):
    job_id: str


class AddPrinterRequest(BaseModel):
    uri: str
    name: str
    description: str | None = None


@router.get("/", response_model=List[dict])
async def list_printers():
    """
    List configured printers in CUPS.
    
    Returns ONLY printers that were explicitly added via POST /add endpoint.
    Printers are never automatically added - full manual control.
    """
    return PrinterManager().list_printers()


@router.get("/{printer_id}/jobs", response_model=List[JobRecord])
async def list_printer_jobs(printer_id: str):
    return PrinterManager().list_jobs(printer_id)


@router.post("/print", response_model=PrintJobResponse)
async def submit_print_job(
    payload: PrintJobRequest,
    file: UploadFile = File(...),
):
    job_id = PrinterManager().submit_job(
        printer_id=payload.printer_id,
        upload=file,
        options=payload.options or {},
    )
    return PrintJobResponse(job_id=job_id)


@router.post("/{printer_id}/test", response_model=PrintJobResponse)
async def print_test_page(printer_id: str):
    job_id = PrinterManager().print_test_page(printer_id)
    return PrintJobResponse(job_id=job_id)


@router.get("/discover", response_model=List[dict])
async def discover_printers():
    """
    Discover available USB and network printers.
    
    **IMPORTANT: This endpoint ONLY discovers printers, it does NOT add them automatically!**
    
    Returns both:
    - USB printers connected to any USB port (auto-detected by CUPS)
    - Wireless printers on the network (via AirPrint/IPP/DNS-SD)
    
    Each printer shows a "configured" flag:
    - `configured: true` - Already added to CUPS, ready to use
    - `configured: false` - Found but NOT added yet (requires manual "Add Printer" action)
    
    **To add a printer:** Use the POST /add endpoint or click "Add Printer" in the Web UI.
    
    Note: Scanner-only devices won't appear here (use /scan/devices for scanners)
    """
    return PrinterManager().discover_devices()


@router.post("/add")
async def add_printer(printer: AddPrinterRequest):
    """
    **Manually** add a USB or network printer to CUPS.
    
    **MANUAL CONTROL ONLY:**
    - Printers are NEVER added automatically
    - This endpoint must be explicitly called (via Web UI button or API)
    - Full control over which printers are configured
    
    **Process:**
    1. Discover printers with GET /discover
    2. User reviews the list
    3. User explicitly clicks "Add Printer" in Web UI
    4. This endpoint is called to add printer to CUPS
    
    **USB Printers:**
    - Auto-detected by CUPS when plugged in
    - No need to specify USB port
    - Use URI from /discover endpoint (e.g., `usb://HP/ENVY%206400`)
    
    **Network Printers:**
    - Use IPP Everywhere driver for compatibility
    - Use URI from /discover (e.g., `ipp://printer.local/ipp/print`)
    """
    try:
        PrinterManager().add_printer(
            uri=printer.uri,
            name=printer.name,
            description=printer.description
        )
        return {"status": "added", "name": printer.name}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{printer_id}")
async def remove_printer(printer_id: str):
    """
    Remove a printer from CUPS.
    
    This permanently deletes the printer configuration.
    Any pending print jobs for this printer will be cancelled.
    """
    try:
        PrinterManager().remove_printer(printer_id)
        return {"status": "removed", "printer_id": printer_id}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
