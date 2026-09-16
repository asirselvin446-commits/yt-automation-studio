from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import ContentCalendar
from app.schemas.dto import CalendarItemDTO

router = APIRouter(prefix="/calendar", tags=["Content Calendar"])


@router.get("", response_model=List[CalendarItemDTO])
async def list_calendar(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(ContentCalendar).order_by(ContentCalendar.scheduled_datetime.asc()))
    return q.scalars().all()


@router.post("")
async def create_calendar_entry(
    title: str,
    scheduled_datetime: datetime,
    notes: str = "",
    db: AsyncSession = Depends(get_db)
):
    entry = ContentCalendar(
        title=title,
        scheduled_datetime=scheduled_datetime,
        notes=notes,
        status="SCHEDULED"
    )
    db.add(entry)
    await db.commit()
    return {"success": True, "id": entry.id}
