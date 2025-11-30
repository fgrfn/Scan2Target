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
    """List available printers."""
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
    
    Returns both:
    - USB printers connected to any USB port (auto-detected by CUPS)
    - Wireless printers on the network (via AirPrint/IPP/DNS-SD)
    
    Note: Scanner-only devices won't appear here (use /scan/devices for scanners)
    """
    return PrinterManager().discover_devices()


@router.post("/add")
async def add_printer(printer: AddPrinterRequest):
    """
    Add a USB or network printer to CUPS.
    
    USB printers are auto-detected - you don't need to specify the USB port.
    Just use the URI from /discover endpoint.
    """
    PrinterManager().add_printer(
        uri=printer.uri,
        name=printer.name,
        description=printer.description
    )
    return {"status": "added", "name": printer.name}
