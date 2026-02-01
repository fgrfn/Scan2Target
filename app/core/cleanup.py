"""Cleanup old scan files and thumbnails to prevent disk from filling up."""
from pathlib import Path
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages cleanup of temporary scan files and thumbnails."""
    
    def __init__(self):
        self.scan_dir = Path('/tmp/scan2target/scans')
        self.thumbnail_max_age_days = 7  # Keep thumbnails for 7 days
        self.failed_scan_max_age_days = 30  # Keep failed upload scans for 30 days
    
    def cleanup_old_thumbnails(self):
        """
        Delete thumbnails older than thumbnail_max_age_days.
        
        Thumbnails are small (~10-50KB) but accumulate over time.
        We keep them for a week for UI preview purposes.
        """
        if not self.scan_dir.exists():
            return
        
        deleted_count = 0
        freed_bytes = 0
        cutoff_time = time.time() - (self.thumbnail_max_age_days * 86400)
        
        logger.info(f"Cleaning up thumbnails older than {self.thumbnail_max_age_days} days...")
        
        for thumb_file in self.scan_dir.glob('*_thumb.jpg'):
            try:
                if thumb_file.stat().st_mtime < cutoff_time:
                    file_size = thumb_file.stat().st_size
                    thumb_file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                    logger.debug(f"  Deleted old thumbnail: {thumb_file.name}")
            except Exception as e:
                logger.warning(f"  Warning: Failed to delete {thumb_file.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"✓ Cleaned up {deleted_count} old thumbnails, freed {freed_bytes / 1024 / 1024:.2f} MB")
        else:
            logger.info("✓ No old thumbnails to clean up")
        
        return {"deleted": deleted_count, "freed_bytes": freed_bytes}
    
    def cleanup_old_failed_scans(self):
        """
        Delete scan files older than failed_scan_max_age_days.
        
        These are scans where upload failed and they are kept for manual retry.
        After 30 days, we assume the user will not retry and delete them.
        """
        if not self.scan_dir.exists():
            return
        
        deleted_count = 0
        freed_bytes = 0
        cutoff_time = time.time() - (self.failed_scan_max_age_days * 86400)
        
        logger.info(f"Cleaning up failed scan files older than {self.failed_scan_max_age_days} days...")
        
        # Find all scan files (not thumbnails)
        for scan_file in self.scan_dir.glob('scan_*.pdf'):
            try:
                if scan_file.stat().st_mtime < cutoff_time:
                    file_size = scan_file.stat().st_size
                    scan_file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                    logger.debug(f"  Deleted old scan: {scan_file.name}")
            except Exception as e:
                logger.warning(f"  Warning: Failed to delete {scan_file.name}: {e}")
        
        # Also check for JPEG files
        for scan_file in self.scan_dir.glob('scan_*.jpg'):
            # Skip thumbnails
            if '_thumb.jpg' in scan_file.name:
                continue
                
            try:
                if scan_file.stat().st_mtime < cutoff_time:
                    file_size = scan_file.stat().st_size
                    scan_file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                    logger.debug(f"  Deleted old scan: {scan_file.name}")
            except Exception as e:
                logger.warning(f"  Warning: Failed to delete {scan_file.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"✓ Cleaned up {deleted_count} old scan files, freed {freed_bytes / 1024 / 1024:.2f} MB")
        else:
            logger.info("✓ No old scan files to clean up")
        
        return {"deleted": deleted_count, "freed_bytes": freed_bytes}
    
    def cleanup_all(self):
        """Run all cleanup tasks."""
        logger.info("=" * 60)
        logger.info("Starting Scan2Target cleanup...")
        logger.info("=" * 60)
        
        thumb_result = self.cleanup_old_thumbnails()
        scan_result = self.cleanup_old_failed_scans()
        
        total_freed = (thumb_result['freed_bytes'] + scan_result['freed_bytes']) / 1024 / 1024
        total_deleted = thumb_result['deleted'] + scan_result['deleted']
        
        logger.info("=" * 60)
        logger.info(f"Cleanup complete: {total_deleted} files deleted, {total_freed:.2f} MB freed")
        logger.info("=" * 60)
        
        return {
            "thumbnails": thumb_result,
            "scans": scan_result,
            "total_freed_mb": total_freed,
            "total_deleted": total_deleted
        }
    
    def get_disk_usage(self):
        """Get current disk usage of scan directory."""
        if not self.scan_dir.exists():
            return {"total_bytes": 0, "file_count": 0, "breakdown": {}}
        
        total_bytes = 0
        file_count = 0
        breakdown = {
            "thumbnails": {"count": 0, "bytes": 0},
            "pdf_scans": {"count": 0, "bytes": 0},
            "jpeg_scans": {"count": 0, "bytes": 0}
        }
        
        for file in self.scan_dir.rglob('*'):
            if file.is_file():
                size = file.stat().st_size
                total_bytes += size
                file_count += 1
                
                if '_thumb.jpg' in file.name:
                    breakdown['thumbnails']['count'] += 1
                    breakdown['thumbnails']['bytes'] += size
                elif file.suffix == '.pdf':
                    breakdown['pdf_scans']['count'] += 1
                    breakdown['pdf_scans']['bytes'] += size
                elif file.suffix == '.jpg':
                    breakdown['jpeg_scans']['count'] += 1
                    breakdown['jpeg_scans']['bytes'] += size
        
        return {
            "total_bytes": total_bytes,
            "total_mb": total_bytes / 1024 / 1024,
            "file_count": file_count,
            "breakdown": breakdown
        }


if __name__ == '__main__':
    # Allow manual execution: python -m app.core.cleanup
    manager = CleanupManager()
    result = manager.cleanup_all()
    
    logger.info("\nCurrent disk usage:")
    usage = manager.get_disk_usage()
    logger.info(f"  Total: {usage['total_mb']:.2f} MB ({usage['file_count']} files)")
    logger.info(f"  Thumbnails: {usage['breakdown']['thumbnails']['bytes'] / 1024 / 1024:.2f} MB ({usage['breakdown']['thumbnails']['count']} files)")
    logger.info(f"  PDF Scans: {usage['breakdown']['pdf_scans']['bytes'] / 1024 / 1024:.2f} MB ({usage['breakdown']['pdf_scans']['count']} files)")
    logger.info(f"  JPEG Scans: {usage['breakdown']['jpeg_scans']['bytes'] / 1024 / 1024:.2f} MB ({usage['breakdown']['jpeg_scans']['count']} files)")
