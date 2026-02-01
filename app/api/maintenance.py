"""Cleanup and maintenance API routes."""
from fastapi import APIRouter

from core.cleanup import CleanupManager

router = APIRouter()


@router.post("/cleanup")
async def trigger_cleanup():
    """
    Manually trigger cleanup of old scan files and thumbnails.
    
    This removes:
    - Thumbnails older than 7 days
    - Failed scan files older than 30 days
    """
    manager = CleanupManager()
    result = manager.cleanup_all()
    return result


@router.get("/disk-usage")
async def get_disk_usage():
    """Get current disk usage statistics for scan directory."""
    manager = CleanupManager()
    usage = manager.get_disk_usage()
    return usage
