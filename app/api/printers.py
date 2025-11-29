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
