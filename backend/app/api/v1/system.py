import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import get_db
from app.models.schema import Video, Notification
from app.schemas.dto import HealthResponse, SystemFolderStats

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def get_health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(select(func.count(Video.id)))
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database_connected=db_ok,
        agent_active=True,
        watch_folder=str(settings.inbox_path),
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/folder-stats", response_model=SystemFolderStats)
async def get_folder_stats():
    settings.ensure_directories()

    def count_files(p: Path) -> int:
        if not p.exists():
            return 0
        return len([f for f in p.iterdir() if f.is_file()])

    return SystemFolderStats(
        root=str(settings.root_path),
        inbox_count=count_files(settings.inbox_path),
        processing_count=count_files(settings.processing_path),
        approved_count=count_files(settings.approved_path),
        uploading_count=count_files(settings.uploading_path),
        uploaded_count=count_files(settings.uploaded_path),
        failed_count=count_files(settings.failed_path),
        archive_count=count_files(settings.archive_path)
    )


@router.get("/notifications")
async def get_notifications(db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(Notification).order_by(Notification.created_at.desc()).limit(30)
    )
    notifications = q.scalars().all()
    return notifications


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Notification).where(Notification.id == notification_id))
    item = q.scalar_one_or_none()
    if item:
        item.is_read = True
        await db.commit()
    return {"success": True}
