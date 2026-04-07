import os
import time
from pathlib import Path
from fastapi import APIRouter, Depends
from app.auth.dependencies import require_admin
from app.config import get_settings

router = APIRouter()
_admin = Depends(require_admin)


@router.post("/cleanup")
def cleanup(_=_admin):
    tmp = Path(get_settings().temp_dir)
    now = time.time()
    deleted_thumbs = deleted_files = 0
    for f in tmp.rglob("*"):
        if not f.is_file():
            continue
        age_days = (now - f.stat().st_mtime) / 86400
        if f.suffix in (".jpg", ".jpeg") and "_thumb" in f.name and age_days > 7:
            f.unlink(); deleted_thumbs += 1
        elif f.suffix in (".pdf", ".jpeg", ".jpg") and age_days > 30:
            f.unlink(); deleted_files += 1
    return {"deleted_thumbnails": deleted_thumbs, "deleted_files": deleted_files}


@router.get("/disk-usage")
def disk_usage(_=_admin):
    tmp = Path(get_settings().temp_dir)
    stats: dict[str, int] = {"thumbnails": 0, "pdfs": 0, "images": 0, "other": 0}
    total = 0
    for f in tmp.rglob("*"):
        if not f.is_file():
            continue
        size = f.stat().st_size
        total += size
        if "_thumb" in f.name:
            stats["thumbnails"] += size
        elif f.suffix == ".pdf":
            stats["pdfs"] += size
        elif f.suffix in (".jpg", ".jpeg", ".tiff"):
            stats["images"] += size
        else:
            stats["other"] += size
    return {"total_bytes": total, "total_mb": round(total / 1024 / 1024, 2), "breakdown": stats}
