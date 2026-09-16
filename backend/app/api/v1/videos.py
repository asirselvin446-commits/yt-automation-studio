import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import security
from app.models.schema import Video, VideoFile, Channel, TitleCandidate, ThumbnailRecord, UploadJob
from app.services.video_service import video_service
from app.services.quality_check_service import quality_checker

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get("")
async def list_videos(
    status: Optional[str] = Query(None),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(Video).options(selectinload(Video.file_info), selectinload(Video.thumbnails)).order_by(desc(Video.created_at))
    if status and status.upper() != "ALL":
        query = query.where(Video.status == status.upper())
    query = query.limit(limit)

    res = await db.execute(query)
    videos = res.scalars().all()

    result = []
    for v in videos:
        thumb = next((th.preview_url or th.local_file_path for th in v.thumbnails if th.is_selected), None)
        result.append({
            "id": v.id,
            "title": v.title,
            "status": v.status,
            "publishing_mode": v.publishing_mode,
            "quality_status": v.quality_status,
            "original_filename": v.original_filename,
            "duration_seconds": float(v.file_info.duration_seconds) if v.file_info else 0.0,
            "file_size_bytes": v.file_info.file_size_bytes if v.file_info else 0,
            "created_at": v.created_at,
            "youtube_video_id": v.youtube_video_id,
            "selected_thumbnail": thumb
        })
    return result


@router.get("/{video_id}")
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    detail = await video_service.get_video_detail(db, video_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check channel connection
    ch_q = await db.execute(select(Channel).where(Channel.is_active == True))
    ch = ch_q.scalar_one_or_none()

    v = detail["video"]
    f = detail["file_info"]
    titles = detail["titles"]
    desc_rec = detail["description"]
    tags_rec = detail["tags"]
    thumbs = detail["thumbnails"]
    summary = detail["summary"]

    selected_title = next((t for t in titles if t.is_selected), titles[0] if titles else None)
    selected_thumb = next((th for th in thumbs if th.is_selected), thumbs[0] if thumbs else None)

    qc = quality_checker.evaluate(
        video=v,
        file_info=f,
        selected_title=selected_title,
        description=desc_rec,
        tags=tags_rec,
        selected_thumbnail=selected_thumb,
        channel_connected=bool(ch)
    )

    return {
        "id": v.id,
        "title": v.title,
        "status": v.status,
        "publishing_mode": v.publishing_mode,
        "quality_status": qc.overall_status,
        "original_filename": v.original_filename,
        "source_path": v.source_path,
        "current_folder_path": v.current_folder_path,
        "youtube_video_id": v.youtube_video_id,
        "youtube_url": v.youtube_url,
        "privacy_status": v.privacy_status,
        "created_at": v.created_at,
        "updated_at": v.updated_at,
        "file_info": {
            "sha256_hash": f.sha256_hash if f else "",
            "file_size_bytes": f.file_size_bytes if f else 0,
            "duration_seconds": float(f.duration_seconds) if f else 0.0,
            "width": f.width if f else None,
            "height": f.height if f else None,
            "fps": float(f.fps) if f and f.fps else None,
            "video_codec": f.video_codec if f else "",
            "audio_codec": f.audio_codec if f else "",
            "has_audio": f.has_audio if f else True,
            "container_format": f.container_format if f else ""
        } if f else None,
        "titles": [
            {
                "id": t.id,
                "candidate_index": t.candidate_index,
                "title_text": t.title_text,
                "reasoning": t.reasoning,
                "estimated_intent": t.estimated_intent,
                "character_length": t.character_length,
                "is_selected": t.is_selected
            } for t in titles
        ],
        "description": {
            "short_description": desc_rec.short_description if desc_rec else "",
            "long_description": desc_rec.long_description if desc_rec else "",
            "call_to_action": desc_rec.call_to_action if desc_rec else "",
            "links_placeholder": desc_rec.links_placeholder if desc_rec else "",
            "hashtags": desc_rec.hashtags if desc_rec else [],
            "chapters": desc_rec.chapters if desc_rec else []
        } if desc_rec else None,
        "tags": {
            "primary_keywords": tags_rec.primary_keywords if tags_rec else [],
            "secondary_keywords": tags_rec.secondary_keywords if tags_rec else [],
            "long_tail_keywords": tags_rec.long_tail_keywords if tags_rec else [],
            "combined_tags_string": tags_rec.combined_tags_string if tags_rec else "",
            "tag_count": tags_rec.tag_count if tags_rec else 0
        } if tags_rec else None,
        "thumbnails": [
            {
                "id": th.id,
                "concept_title": th.concept_title,
                "text_suggestions": th.text_suggestions,
                "visual_composition": th.visual_composition,
                "preview_url": th.preview_url,
                "local_file_path": th.local_file_path,
                "is_selected": th.is_selected,
                "status": th.status
            } for th in thumbs
        ],
        "quality_check": qc.model_dump(),
        "transcript_summary": summary
    }


@router.post("/{video_id}/approve")
async def approve_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Human approval transition: moves video to APPROVED state and folder."""
    q = await db.execute(select(Video).where(Video.id == video_id))
    video = q.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    settings.ensure_directories()
    filename = os.path.basename(video.current_folder_path)
    dest_path = settings.approved_path / filename

    try:
        if os.path.exists(video.current_folder_path) and Path(video.current_folder_path).resolve() != dest_path.resolve():
            shutil.move(video.current_folder_path, str(dest_path))
            video.current_folder_path = str(dest_path)
    except Exception as e:
        pass

    video.status = "APPROVED"
    video.quality_status = "READY"

    # Queue an UploadJob
    upload_job = UploadJob(
        video_id=video.id,
        status="QUEUED"
    )
    db.add(upload_job)

    await db.commit()
    return {"success": True, "status": "APPROVED", "message": "Video approved and queued for upload."}


@router.post("/{video_id}/reject")
async def reject_video(video_id: str, reason: str = "Rejected by creator", db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Video).where(Video.id == video_id))
    video = q.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    settings.ensure_directories()
    filename = os.path.basename(video.current_folder_path)
    dest_path = settings.failed_path / filename

    try:
        if os.path.exists(video.current_folder_path) and Path(video.current_folder_path).resolve() != dest_path.resolve():
            shutil.move(video.current_folder_path, str(dest_path))
            video.current_folder_path = str(dest_path)
    except Exception as e:
        pass

    video.status = "CANCELLED"
    video.notes = f"Rejected: {reason}"
    await db.commit()
    return {"success": True, "status": "CANCELLED"}


@router.post("/{video_id}/select-title/{title_id}")
async def select_title(video_id: str, title_id: str, db: AsyncSession = Depends(get_db)):
    # Unselect all other titles for this video
    q = await db.execute(
        select(TitleCandidate).join(Video.metadata_generations).where(Video.id == video_id)
    )
    titles = q.scalars().all()
    for t in titles:
        t.is_selected = (t.id == title_id)
    await db.commit()
    return {"success": True}


@router.post("/manual-ingest")
async def manual_ingest(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Allow manual video ingestion directly through Studio UI."""
    settings.ensure_directories()
    sanitized = security.sanitize_filename(file.filename or "uploaded_video.mp4")
    dest = settings.inbox_path / sanitized
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"success": True, "message": f"Saved to INBOX: {sanitized}", "path": str(dest)}


@router.post("/internal-register")
async def internal_register(payload: dict, db: AsyncSession = Depends(get_db)):
    """Called by local watcher agent to ingest and evaluate newly detected media."""
    res = await video_service.register_detected_video(
        db=db,
        source_path=payload["source_path"],
        sha256_hash=payload["sha256_hash"],
        file_size=payload["file_size_bytes"],
        duration=payload["duration_seconds"],
        width=payload.get("width"),
        height=payload.get("height"),
        fps=payload.get("fps"),
        video_codec=payload.get("video_codec"),
        audio_codec=payload.get("audio_codec"),
        has_audio=payload.get("has_audio", True)
    )
    if res.get("success") and res.get("video_id"):
        # Trigger background AI analysis
        await video_service.run_ai_pipeline(db, res["video_id"])
    return res


@router.post("/{video_id}/trigger-ai")
async def trigger_ai_rerun(video_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger AI metadata regeneration."""
    success = await video_service.run_ai_pipeline(db, video_id)
    return {"success": success}
