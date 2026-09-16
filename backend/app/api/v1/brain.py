from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import Channel, Video, ChannelInsight
from app.schemas.dto import BrainQueryRequest, BrainQueryResponse
from app.integrations.ai.factory import ai_factory

router = APIRouter(prefix="/brain", tags=["Channel Brain"])


@router.post("/query", response_model=BrainQueryResponse)
async def query_channel_brain(req: BrainQueryRequest, db: AsyncSession = Depends(get_db)):
    # Gather historical channel context
    ch_q = await db.execute(select(Channel).where(Channel.is_active == True))
    channel = ch_q.scalar_one_or_none()

    videos_q = await db.execute(select(Video).limit(20))
    videos = videos_q.scalars().all()

    context = {
        "channel_title": channel.title if channel else "Unconnected Channel",
        "subscribers": channel.subscriber_count if channel else 0,
        "views": channel.view_count if channel else 0,
        "videos": [{"title": v.title, "status": v.status} for v in videos]
    }

    provider = ai_factory.get_provider()
    res = await provider.analyze_channel_insights(req.question, context)

    insight = ChannelInsight(
        channel_id=channel.id if channel else None,
        query_text=req.question,
        insight_type="custom_qa",
        data_basis=res.get("data_basis", {}),
        interpretation=res.get("interpretation", ""),
        actionable_suggestions=res.get("actionable_suggestions", []),
        confidence_rating=res.get("confidence_rating", "HIGH")
    )
    db.add(insight)
    await db.commit()

    return BrainQueryResponse(
        data_basis=res.get("data_basis", {}),
        interpretation=res.get("interpretation", ""),
        actionable_suggestions=res.get("actionable_suggestions", []),
        confidence_rating=res.get("confidence_rating", "HIGH")
    )


@router.get("/history")
async def get_brain_history(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(ChannelInsight).order_by(ChannelInsight.created_at.desc()).limit(15))
    return q.scalars().all()
