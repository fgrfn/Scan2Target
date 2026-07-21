"""Persistent, resumable multi-page scan session routes."""
from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from api.scan import _get_scanner
from core.scanning.manager import ScannerManager
from core.scanning.sessions import FinalizeResult, ScanSession, ScanSessionService
from core.validation import sanitize_filename_prefix

router = APIRouter()


class CreateSessionRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=512)
    profile_id: str = Field(min_length=1, max_length=128)
    target_id: str | None = Field(default=None, max_length=128)
    source: str = Field(default="Flatbed", min_length=1, max_length=64)
    capture_mode: Literal["interactive", "automatic"] = "interactive"


class ReorderPagesRequest(BaseModel):
    page_ids: list[str] = Field(min_length=1, max_length=100)


class FinalizeSessionRequest(BaseModel):
    target_id: str = Field(min_length=1, max_length=128)
    filename_prefix: str | None = Field(default=None, max_length=128)
    optimize: bool = True
    remove_blank_pages: bool = False
    ocr: bool = False
    pdfa: bool = False
    ocr_language: str = Field(default="deu+eng", pattern=r"^[a-z]{3}(\+[a-z]{3})*$")

    @field_validator("filename_prefix")
    @classmethod
    def safe_filename(cls, value: str | None):
        return sanitize_filename_prefix(value, "scan") if value is not None else None


def _service() -> ScanSessionService:
    return ScanSessionService()


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=410, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, RuntimeError) and "busy" in str(exc).lower():
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc) or "Scan session operation failed")


@router.get("/sessions", response_model=list[ScanSession])
async def list_scan_sessions():
    return await asyncio.to_thread(_service().list_active)


@router.post("/sessions", response_model=ScanSession, status_code=201)
async def create_scan_session(payload: CreateSessionRequest):
    device = _get_scanner(payload.device_id)
    ScannerManager().resolve_profile(payload.profile_id)
    if payload.capture_mode == "automatic" and not payload.source.lower().startswith("adf"):
        raise HTTPException(
            status_code=422,
            detail="Automatic stack mode is only available for an ADF source",
        )
    try:
        return await asyncio.to_thread(
            _service().create,
            device_id=payload.device_id,
            device_uri=device.uri,
            profile_id=payload.profile_id,
            target_id=payload.target_id,
            source=payload.source,
            capture_mode=payload.capture_mode,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/sessions/{session_id}", response_model=ScanSession)
async def get_scan_session(session_id: str):
    try:
        return await asyncio.to_thread(_service().get, session_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/sessions/{session_id}/capture", response_model=ScanSession)
async def capture_session_pages(session_id: str):
    try:
        return await asyncio.to_thread(_service().capture, session_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/sessions/{session_id}/pages/{page_id}/image")
async def get_session_page_image(session_id: str, page_id: str):
    try:
        preview = await asyncio.to_thread(_service().page_preview, session_id, page_id)
        return Response(
            content=preview,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/sessions/{session_id}/pages/{page_id}", response_model=ScanSession)
async def remove_session_page(session_id: str, page_id: str):
    try:
        return await asyncio.to_thread(_service().remove_page, session_id, page_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/sessions/{session_id}/pages/{page_id}/rotate", response_model=ScanSession)
async def rotate_session_page(session_id: str, page_id: str):
    try:
        return await asyncio.to_thread(_service().rotate, session_id, page_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.put("/sessions/{session_id}/pages", response_model=ScanSession)
async def reorder_session_pages(session_id: str, payload: ReorderPagesRequest):
    try:
        return await asyncio.to_thread(_service().reorder, session_id, payload.page_ids)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/sessions/{session_id}", status_code=204)
async def cancel_scan_session(session_id: str):
    try:
        await asyncio.to_thread(_service().cancel, session_id)
        return Response(status_code=204)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeResult)
async def finalize_scan_session(session_id: str, payload: FinalizeSessionRequest):
    try:
        return await asyncio.to_thread(
            _service().finalize,
            session_id,
            target_id=payload.target_id,
            filename_prefix=payload.filename_prefix,
            optimize=payload.optimize,
            remove_blank_pages=payload.remove_blank_pages,
            ocr=payload.ocr,
            pdfa=payload.pdfa,
            ocr_language=payload.ocr_language,
        )
    except Exception as exc:
        raise _http_error(exc) from exc
