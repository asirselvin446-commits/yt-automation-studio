"""
Notification Service — Manages in-app notifications for YT Automation Studio.
Dispatches notifications for pipeline events, AI completions, upload status,
and system alerts. Persists notifications to the database.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from app.models.schema import Notification
from app.core.logging import system_logger


class NotificationService:
    """In-app notification dispatcher and manager."""

    # Notification severity levels
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    # Notification categories
    PIPELINE = "pipeline"
    AI = "ai"
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    SYSTEM = "system"
    ANALYTICS = "analytics"

    async def create(
        self,
        db: AsyncSession,
        title: str,
        message: str,
        severity: str = "info",
        category: str = "system",
        action_url: Optional[str] = None,
        video_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create and persist a new notification.

        Args:
            db: Async database session.
            title: Short notification title.
            message: Detailed notification body.
            severity: 'info', 'success', 'warning', or 'error'.
            category: Notification category for filtering.
            action_url: Deep-link URL for actionable notifications.
            video_id: Optional linked video ID.
            metadata: Optional JSON-serializable extra data.
        """
        notification = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            severity=severity,
            category=category,
            action_url=action_url,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(notification)
        await db.flush()

        system_logger.info(f"[Notification] [{severity.upper()}] {title}: {message[:100]}")
        return notification

    async def get_all(
        self, db: AsyncSession, limit: int = 50, unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent notifications, optionally filtered to unread only."""
        query = select(Notification).order_by(desc(Notification.created_at)).limit(limit)
        if unread_only:
            query = query.where(Notification.is_read == False)

        result = await db.execute(query)
        notifications = result.scalars().all()

        return [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "severity": n.severity,
                "category": getattr(n, "category", "system"),
                "action_url": getattr(n, "action_url", None),
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]

    async def mark_read(self, db: AsyncSession, notification_id: str) -> bool:
        """Mark a specific notification as read."""
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        return result.rowcount > 0

    async def mark_all_read(self, db: AsyncSession) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        stmt = (
            update(Notification)
            .where(Notification.is_read == False)
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        return result.rowcount

    async def get_unread_count(self, db: AsyncSession) -> int:
        """Get count of unread notifications."""
        query = select(Notification).where(Notification.is_read == False)
        result = await db.execute(query)
        return len(result.scalars().all())

    # ── Convenience dispatchers ───────────────────────────────────────

    async def notify_video_ingested(self, db: AsyncSession, filename: str, video_id: str):
        return await self.create(
            db, title="Video Ingested",
            message=f"New video detected and ingested: {filename}",
            severity=self.INFO, category=self.PIPELINE,
            action_url=f"/videos/{video_id}",
        )

    async def notify_ai_complete(self, db: AsyncSession, filename: str, video_id: str):
        return await self.create(
            db, title="AI Analysis Complete",
            message=f"Titles, description, and tags generated for: {filename}",
            severity=self.SUCCESS, category=self.AI,
            action_url=f"/videos/{video_id}",
        )

    async def notify_ready_for_approval(self, db: AsyncSession, filename: str, video_id: str):
        return await self.create(
            db, title="Ready for Approval",
            message=f"Video is ready for your review: {filename}",
            severity=self.INFO, category=self.PIPELINE,
            action_url=f"/videos/{video_id}",
        )

    async def notify_upload_complete(self, db: AsyncSession, filename: str, youtube_url: str):
        return await self.create(
            db, title="Upload Complete",
            message=f"Video uploaded successfully: {filename}",
            severity=self.SUCCESS, category=self.UPLOAD,
            action_url=youtube_url,
        )

    async def notify_upload_failed(self, db: AsyncSession, filename: str, error: str):
        return await self.create(
            db, title="Upload Failed",
            message=f"Upload failed for {filename}: {error}",
            severity=self.ERROR, category=self.UPLOAD,
        )

    async def notify_channel_connected(self, db: AsyncSession, channel_title: str):
        return await self.create(
            db, title="Channel Connected",
            message=f"YouTube channel connected: {channel_title}",
            severity=self.SUCCESS, category=self.YOUTUBE,
            action_url="/analytics",
        )

    async def notify_agent_offline(self, db: AsyncSession):
        return await self.create(
            db, title="Agent Offline",
            message="The local watcher agent has gone offline. Video monitoring paused.",
            severity=self.WARNING, category=self.SYSTEM,
        )


# Singleton
notification_service = NotificationService()
