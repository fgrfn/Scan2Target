"""Cleanup, database backup and maintenance API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.cleanup import CleanupManager
from core.database import get_db

router = APIRouter()


class RestoreRequest(BaseModel):
    name: str
    confirmation: str


@router.post("/cleanup")
async def trigger_cleanup():
    """Remove expired thumbnails and abandoned scan files."""
    return CleanupManager().cleanup_all()


@router.get("/disk-usage")
async def get_disk_usage():
    return CleanupManager().get_disk_usage()


@router.post("/database/backup")
async def create_database_backup():
    path = get_db().create_backup(label="manual")
    return {"status": "created", "name": path.name, "size": path.stat().st_size}


@router.get("/database/backups")
async def list_database_backups():
    return get_db().list_backups()


@router.get("/database/backups/{name}")
async def download_database_backup(name: str):
    database = get_db()
    path = (database.backup_dir / Path(name).name).resolve()
    if path.parent != database.backup_dir.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(path, filename=path.name, media_type="application/vnd.sqlite3")


@router.post("/database/restore")
async def restore_database_backup(payload: RestoreRequest):
    if payload.confirmation != "RESTORE":
        raise HTTPException(status_code=400, detail="confirmation must be RESTORE")
    try:
        path = get_db().restore_backup(payload.name)
        return {
            "status": "restored",
            "database": str(path),
            "restart_recommended": True,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/database/integrity")
async def database_integrity():
    result = get_db().integrity_check()
    if not result["ok"]:
        raise HTTPException(status_code=503, detail=result)
    return result


@router.get("/database/export")
async def export_database_json():
    path = get_db().export_json()
    return FileResponse(path, filename=path.name, media_type="application/json")
