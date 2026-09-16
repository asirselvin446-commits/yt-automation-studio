from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import Channel

router = APIRouter(prefix="/monetization", tags=["Monetization Dashboard"])


@router.get("")
async def get_monetization_status(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Channel).where(Channel.is_active == True))
    channel = q.scalar_one_or_none()

    subs = channel.subscriber_count if channel else 0
    # Requirement benchmarks from official YPP
    return {
        "is_connected": bool(channel),
        "disclaimer": "Eligibility thresholds do not guarantee monetization approval. Applications undergo strict human & automated YouTube policy review.",
        "thresholds": {
            "subscribers": {
                "current": subs,
                "required": 1000,
                "progress_percent": min(100.0, round((subs / 1000.0) * 100, 1)),
                "eligible": subs >= 1000
            },
            "watch_hours": {
                "current": 0,
                "required": 4000,
                "progress_percent": 0.0,
                "eligible": False
            },
            "shorts_views": {
                "current": 0,
                "required": 10000000,
                "progress_percent": 0.0,
                "eligible": False
            }
        },
        "stages": [
            {"step": 1, "name": "Eligibility Thresholds", "status": "In Progress"},
            {"step": 2, "name": "2-Step Verification", "status": "Recommended"},
            {"step": 3, "name": "Follow Community Guidelines", "status": "Good Standing"},
            {"step": 4, "name": "Apply for Review", "status": "Locked until eligible"}
        ]
    }
