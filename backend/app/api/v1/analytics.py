from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import Channel, AnalyticsSnapshot

router = APIRouter(prefix="/analytics", tags=["YouTube Analytics"])


@router.get("")
async def get_analytics(
    timeframe: str = Query("28d", pattern="^(today|7d|28d|90d|lifetime)$"),
    db: AsyncSession = Depends(get_db)
):
    q = await db.execute(select(Channel).where(Channel.is_active == True))
    channel = q.scalar_one_or_none()
    if not channel:
        return {
            "is_connected": False,
            "message": "Connect YouTube to view live channel analytics.",
            "metrics": None,
            "charts": []
        }

    # Fetch snapshots if available
    snaps_q = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.channel_id == channel.id)
        .order_by(AnalyticsSnapshot.snapshot_date.asc())
    )
    snaps = snaps_q.scalars().all()

    return {
        "is_connected": True,
        "timeframe": timeframe,
        "metrics": {
            "subscribers": channel.subscriber_count,
            "total_views": channel.view_count,
            "video_count": channel.video_count,
            "estimated_revenue": 0.0,
            "average_retention": "0%",
            "average_ctr": "0%"
        },
        "charts": [
            {
                "date": s.snapshot_date.strftime("%Y-%m-%d"),
                "views": s.views,
                "subscribers": s.subscribers_gained,
                "watch_time": float(s.watch_time_minutes)
            } for s in snaps
        ]
    }
