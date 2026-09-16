from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import Channel, YouTubeConnection
from app.integrations.youtube.oauth import youtube_oauth

router = APIRouter(prefix="/youtube", tags=["YouTube Integration"])


@router.get("/status")
async def get_channel_status(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Channel).where(Channel.is_active == True))
    channel = q.scalar_one_or_none()
    if not channel:
        return {
            "is_connected": False,
            "message": "Connect YouTube to view live channel analytics and enable uploads."
        }

    return {
        "is_connected": True,
        "channel_id": channel.youtube_channel_id,
        "title": channel.title,
        "custom_url": channel.custom_url,
        "thumbnail_url": channel.thumbnail_url,
        "subscriber_count": channel.subscriber_count,
        "video_count": channel.video_count,
        "view_count": channel.view_count
    }


@router.get("/connect-url")
async def get_connect_url():
    res = youtube_oauth.get_authorization_url()
    return res


@router.get("/oauth2callback")
async def oauth2_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    tokens = await youtube_oauth.exchange_code_for_tokens(code)
    if "error" in tokens:
        raise HTTPException(status_code=400, detail=tokens["error"])
    return {"success": True, "message": "YouTube channel connected successfully."}


@router.post("/disconnect")
async def disconnect_channel(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Channel))
    channels = q.scalars().all()
    for ch in channels:
        ch.is_active = False
    await db.commit()
    return {"success": True, "message": "YouTube disconnected."}
