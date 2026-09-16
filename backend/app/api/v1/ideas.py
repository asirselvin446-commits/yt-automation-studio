from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.schema import ContentIdea
from app.schemas.dto import ContentIdeaCreateDTO, ContentIdeaDTO
from app.integrations.ai.factory import ai_factory

router = APIRouter(prefix="/ideas", tags=["Content Ideas"])


@router.get("", response_model=List[ContentIdeaDTO])
async def list_ideas(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(ContentIdea).order_by(desc(ContentIdea.created_at)))
    ideas = q.scalars().all()
    return ideas


@router.post("/generate")
async def generate_ideas(req: ContentIdeaCreateDTO, db: AsyncSession = Depends(get_db)):
    provider = ai_factory.get_provider()
    raw_ideas = await provider.generate_ideas(
        topic=req.topic,
        niche=req.niche,
        audience=req.target_audience,
        count=10
    )

    created_ideas = []
    for item in raw_ideas:
        idea = ContentIdea(
            topic=item.get("topic", req.topic),
            title_concept=item.get("title_concept", "Engaging Video Idea"),
            hook=item.get("hook", ""),
            video_structure=item.get("video_structure", ""),
            target_audience=item.get("target_audience", req.target_audience or "General viewers"),
            production_difficulty=item.get("production_difficulty", "Medium"),
            estimated_length_minutes=req.estimated_length_minutes,
            status="IDEA"
        )
        db.add(idea)
        created_ideas.append(idea)

    await db.commit()
    return {"success": True, "count": len(created_ideas)}


@router.patch("/{idea_id}/status")
async def update_idea_status(idea_id: str, status: str, db: AsyncSession = Depends(get_db)):
    valid_statuses = ["IDEA", "SCRIPT", "IN_PRODUCTION", "COMPLETED", "ARCHIVED"]
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    q = await db.execute(select(ContentIdea).where(ContentIdea.id == idea_id))
    idea = q.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    idea.status = status.upper()
    await db.commit()
    return {"success": True, "status": idea.status}


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(ContentIdea).where(ContentIdea.id == idea_id))
    idea = q.scalar_one_or_none()
    if idea:
        await db.delete(idea)
        await db.commit()
    return {"success": True}
