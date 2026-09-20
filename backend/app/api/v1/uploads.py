"""Live cloud-pipeline view: the real state of every ingested video.

Reads Supabase ingest_items directly (source of truth for the GitHub Actions
uploader) so the desktop app can show and manage uploads in real time.
"""
from fastapi import APIRouter, HTTPException
from app.services import supabase_ingest_service

router = APIRouter(prefix="/uploads", tags=["Cloud Uploads"])


@router.get("")
async def list_uploads():
    """Every video in the pipeline with its stage (HELD/QUEUED/PROCESSING/UPLOADED/FAILED)."""
    return supabase_ingest_service.list_items()


@router.post("/{item_id}/publish")
async def publish_item(item_id: str):
    """Release a HELD video to the upload queue (Review-mode approval)."""
    released = supabase_ingest_service.release_held(item_id)
    if not released:
        raise HTTPException(status_code=400, detail="Video is not held or was already released.")
    return {"success": True}


@router.post("/{item_id}/retry")
async def retry_item(item_id: str):
    """Re-queue a FAILED video for another upload attempt."""
    if not supabase_ingest_service.retry_item(item_id):
        raise HTTPException(status_code=400, detail="Video is not in a FAILED state.")
    return {"success": True}
