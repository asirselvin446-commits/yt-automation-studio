"""
Audit Service — Immutable audit logging for every significant action
in YT Automation Studio. Logs user actions, AI calls, file movements,
YouTube API interactions, and system events.
"""
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.schema import AuditLog
from app.core.logging import system_logger


class AuditService:
    """Immutable audit trail for all studio operations."""

    # Action categories
    VIDEO = "video"
    AI = "ai"
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    FILE = "file"
    SETTINGS = "settings"
    AUTH = "auth"
    SYSTEM = "system"

    async def log(
        self,
        db: AsyncSession,
        action: str,
        category: str = "system",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Record an immutable audit log entry.

        Args:
            db: Database session.
            action: Human-readable action description (e.g., "video.approved").
            category: Action category for filtering.
            entity_type: Type of entity affected (e.g., "video", "channel").
            entity_id: ID of the affected entity.
            details: JSON-serializable extra context.
            user_agent: HTTP user-agent string (if from web request).
            ip_address: Client IP address (if from web request).
        """
        entry = AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        await db.flush()

        system_logger.debug(f"[Audit] {category}.{action} entity={entity_type}:{entity_id}")
        return entry

    async def get_recent(
        self, db: AsyncSession, limit: int = 100, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent audit log entries."""
        query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        if category:
            query = query.where(AuditLog.category == category)

        result = await db.execute(query)
        entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "action": e.action,
                "category": e.category,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": json.loads(e.details) if e.details else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]

    async def get_entity_history(
        self, db: AsyncSession, entity_type: str, entity_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all audit entries for a specific entity."""
        query = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        entries = result.scalars().all()

        return [
            {
                "id": e.id,
                "action": e.action,
                "details": json.loads(e.details) if e.details else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]

    # ── Convenience loggers ───────────────────────────────────────────

    async def log_video_ingested(self, db: AsyncSession, video_id: str, filename: str):
        return await self.log(
            db, action="ingested", category=self.VIDEO,
            entity_type="video", entity_id=video_id,
            details={"filename": filename},
        )

    async def log_video_approved(self, db: AsyncSession, video_id: str, title: str):
        return await self.log(
            db, action="approved", category=self.VIDEO,
            entity_type="video", entity_id=video_id,
            details={"title": title},
        )

    async def log_video_rejected(self, db: AsyncSession, video_id: str, reason: str):
        return await self.log(
            db, action="rejected", category=self.VIDEO,
            entity_type="video", entity_id=video_id,
            details={"reason": reason},
        )

    async def log_ai_generation(
        self, db: AsyncSession, video_id: str, provider: str,
        generation_type: str, tokens_used: int = 0
    ):
        return await self.log(
            db, action="ai_generation", category=self.AI,
            entity_type="video", entity_id=video_id,
            details={
                "provider": provider,
                "type": generation_type,
                "tokens_used": tokens_used,
            },
        )

    async def log_upload_started(self, db: AsyncSession, video_id: str, channel_id: str):
        return await self.log(
            db, action="upload_started", category=self.UPLOAD,
            entity_type="video", entity_id=video_id,
            details={"channel_id": channel_id},
        )

    async def log_upload_completed(
        self, db: AsyncSession, video_id: str, youtube_video_id: str
    ):
        return await self.log(
            db, action="upload_completed", category=self.UPLOAD,
            entity_type="video", entity_id=video_id,
            details={"youtube_video_id": youtube_video_id},
        )

    async def log_upload_failed(self, db: AsyncSession, video_id: str, error: str):
        return await self.log(
            db, action="upload_failed", category=self.UPLOAD,
            entity_type="video", entity_id=video_id,
            details={"error": error},
        )

    async def log_file_moved(
        self, db: AsyncSession, video_id: str, from_stage: str, to_stage: str
    ):
        return await self.log(
            db, action="file_moved", category=self.FILE,
            entity_type="video", entity_id=video_id,
            details={"from": from_stage, "to": to_stage},
        )

    async def log_channel_connected(self, db: AsyncSession, channel_id: str, channel_title: str):
        return await self.log(
            db, action="channel_connected", category=self.YOUTUBE,
            entity_type="channel", entity_id=channel_id,
            details={"title": channel_title},
        )

    async def log_settings_changed(self, db: AsyncSession, setting_name: str, old_value: Any, new_value: Any):
        return await self.log(
            db, action="settings_changed", category=self.SETTINGS,
            entity_type="settings", entity_id=setting_name,
            details={"old": str(old_value), "new": str(new_value)},
        )


# Singleton
audit_service = AuditService()
