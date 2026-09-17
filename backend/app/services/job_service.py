"""
Job Queue Service — Manages background job execution for YT Automation Studio.
Tracks AI generation jobs, upload jobs, analytics sync jobs, and other
long-running operations with status tracking and retry management.
"""
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from app.models.schema import UploadJob
from app.core.logging import system_logger


class JobService:
    """Background job queue manager."""

    # Job types
    AI_ANALYSIS = "ai_analysis"
    AI_TITLES = "ai_titles"
    AI_DESCRIPTION = "ai_description"
    AI_TAGS = "ai_tags"
    AI_THUMBNAILS = "ai_thumbnails"
    UPLOAD = "upload"
    ANALYTICS_SYNC = "analytics_sync"
    TRANSCRIPT = "transcript"

    # Job statuses
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    async def create_job(
        self,
        db: AsyncSession,
        job_type: str,
        video_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """
        Create a new background job entry.

        Args:
            db: Database session.
            job_type: Type of job (ai_analysis, upload, etc.).
            video_id: Optional linked video.
            channel_id: Optional linked channel.
            params: Job-specific parameters.
            priority: 0 = normal, higher = higher priority.

        Returns:
            Job dict with id, type, and status.
        """
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()

        job = UploadJob(
            id=job_id,
            video_id=video_id,
            channel_id=channel_id,
            status=self.QUEUED,
            privacy_status="private",
            retry_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        await db.flush()

        system_logger.info(f"Job created: {job_type} (id={job_id[:8]}...)")

        return {
            "id": job_id,
            "type": job_type,
            "status": self.QUEUED,
            "video_id": video_id,
            "created_at": now.isoformat(),
        }

    async def update_status(
        self,
        db: AsyncSession,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update a job's status and optional progress/result data.

        Args:
            db: Database session.
            job_id: Job ID.
            status: New status (RUNNING, COMPLETED, FAILED, CANCELLED).
            progress: Optional progress percentage (0-100).
            result: Optional result data.
            error_message: Optional error description.
        """
        values = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if error_message:
            values["error_response"] = error_message

        stmt = update(UploadJob).where(UploadJob.id == job_id).values(**values)
        res = await db.execute(stmt)

        if status == self.FAILED:
            system_logger.warning(f"Job failed: {job_id[:8]}... — {error_message}")
        elif status == self.COMPLETED:
            system_logger.info(f"Job completed: {job_id[:8]}...")

        return res.rowcount > 0

    async def get_job(self, db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID."""
        result = await db.execute(select(UploadJob).where(UploadJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None

        return self._to_dict(job)

    async def list_jobs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        video_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering."""
        query = select(UploadJob).order_by(desc(UploadJob.created_at)).limit(limit)
        if status:
            query = query.where(UploadJob.status == status)
        if video_id:
            query = query.where(UploadJob.video_id == video_id)

        result = await db.execute(query)
        jobs = result.scalars().all()
        return [self._to_dict(j) for j in jobs]

    async def get_active_jobs(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all currently running or queued jobs."""
        query = (
            select(UploadJob)
            .where(UploadJob.status.in_([self.QUEUED, self.RUNNING]))
            .order_by(UploadJob.created_at)
        )
        result = await db.execute(query)
        return [self._to_dict(j) for j in result.scalars().all()]

    async def cancel_job(self, db: AsyncSession, job_id: str) -> bool:
        """Cancel a queued or running job."""
        stmt = (
            update(UploadJob)
            .where(
                UploadJob.id == job_id,
                UploadJob.status.in_([self.QUEUED, self.RUNNING]),
            )
            .values(status=self.CANCELLED, updated_at=datetime.utcnow())
        )
        res = await db.execute(stmt)
        if res.rowcount > 0:
            system_logger.info(f"Job cancelled: {job_id[:8]}...")
            return True
        return False

    async def retry_job(self, db: AsyncSession, job_id: str) -> bool:
        """Reset a failed job back to QUEUED for retry."""
        result = await db.execute(select(UploadJob).where(UploadJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job or job.status != self.FAILED:
            return False

        stmt = (
            update(UploadJob)
            .where(UploadJob.id == job_id)
            .values(
                status=self.QUEUED,
                retry_count=job.retry_count + 1,
                error_response=None,
                updated_at=datetime.utcnow(),
            )
        )
        await db.execute(stmt)
        system_logger.info(f"Job queued for retry: {job_id[:8]}... (attempt {job.retry_count + 1})")
        return True

    async def get_stats(self, db: AsyncSession) -> Dict[str, int]:
        """Get job counts by status."""
        result = await db.execute(select(UploadJob))
        jobs = result.scalars().all()

        stats = {self.QUEUED: 0, self.RUNNING: 0, self.COMPLETED: 0, self.FAILED: 0, self.CANCELLED: 0}
        for j in jobs:
            status = j.status
            if status in stats:
                stats[status] += 1
        return stats

    @staticmethod
    def _to_dict(job: UploadJob) -> Dict[str, Any]:
        return {
            "id": job.id,
            "video_id": job.video_id,
            "channel_id": job.channel_id,
            "status": job.status,
            "privacy_status": job.privacy_status,
            "retry_count": job.retry_count,
            "error": job.error_response,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


# Singleton
job_service = JobService()
