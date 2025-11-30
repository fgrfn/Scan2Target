"""Unified history routes."""
from typing import List
from fastapi import APIRouter

from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobRecord

router = APIRouter()


@router.get("/", response_model=List[JobRecord])
async def list_history():
    """Return unified scan/print history."""
    import time
    start = time.time()
    result = JobManager().list_history()
    print(f"[TIMING] list_history: took {time.time() - start:.3f}s")
    return result
