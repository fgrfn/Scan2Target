"""Unified history routes."""
from typing import List
from fastapi import APIRouter, HTTPException

from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobRecord
from app.core.targets.manager import TargetManager

router = APIRouter()


@router.get("/", response_model=List[JobRecord])
async def list_history():
    """Return unified scan/print history."""
    import time
    start = time.time()
    result = JobManager().list_history()
    print(f"[TIMING] list_history: took {time.time() - start:.3f}s")
    return result


@router.delete("/")
async def clear_history():
    """Clear all completed jobs from history."""
    try:
        job_manager = JobManager()
        # Only delete completed jobs, keep active ones
        deleted_count = job_manager.clear_completed_jobs()
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} completed jobs",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a single job from history."""
    try:
        job_manager = JobManager()
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Delete associated file if it exists
        if job.file_path:
            from pathlib import Path
            file_path = Path(job.file_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"✓ Deleted scan file: {file_path}")
                except Exception as cleanup_error:
                    print(f"Warning: Failed to delete file: {cleanup_error}")
        
        # Delete job from database
        success = job_manager.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete job")
        
        return {
            "status": "success",
            "message": f"Job {job_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running or queued job.
    
    This stops the background task and marks the job as cancelled.
    Only works for jobs in 'queued' or 'running' status.
    """
    try:
        job_manager = JobManager()
        success = job_manager.cancel_job(job_id)
        
        if not success:
            job = job_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Job cannot be cancelled (status: {job.status})"
                )
        
        return {
            "status": "success",
            "message": f"Job {job_id} cancelled successfully",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/retry-upload")
async def retry_upload(job_id: str):
    """
    Manually retry upload for a failed job.
    
    This allows users to retry delivery after fixing target connection issues.
    The scan file must still exist locally.
    """
    try:
        job_manager = JobManager()
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if not job.file_path:
            raise HTTPException(status_code=400, detail="No file path found for this job")
        
        # Check if file still exists
        from pathlib import Path
        file_path = Path(job.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=400, detail="Scan file no longer exists on disk")
        
        # Retry delivery
        print(f"Manual retry upload for job {job_id} to target {job.target_id}")
        
        try:
            TargetManager().deliver(job.target_id, job.file_path, {'job_id': job_id})
            
            # Update job to clear error message
            job.message = None
            job_manager.update_job(job)
            
            # Clean up local file after successful retry
            try:
                file_path.unlink()
                print(f"✓ Deleted scan file after successful retry: {file_path}")
            except Exception as cleanup_error:
                print(f"Warning: Failed to delete file after retry: {cleanup_error}")
            
            return {
                "status": "success",
                "message": f"Upload successful to {job.target_id}",
                "job_id": job_id
            }
            
        except Exception as delivery_error:
            # Update job with new error message
            job.message = f"Upload failed: {str(delivery_error)}"
            job_manager.update_job(job)
            
            raise HTTPException(
                status_code=400,
                detail=f"Upload failed: {str(delivery_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
