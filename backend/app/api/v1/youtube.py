from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.security import security
from app.core.logging import upload_logger
from app.models.schema import Channel, YouTubeConnection
from app.integrations.youtube.oauth import youtube_oauth
from app.integrations.youtube.client import YouTubeClient

router = APIRouter(prefix="/youtube", tags=["YouTube Integration"])


def _callback_page(title: str, message: str, ok: bool) -> str:
    """Small self-contained page shown in the browser after the OAuth redirect."""
    color = "#22c55e" if ok else "#ef4444"
    icon = "&#10003;" if ok else "&#10007;"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title}</title><style>
html,body{{height:100%;margin:0}}
body{{background:#090a0f;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;
display:flex;align-items:center;justify-content:center}}
.card{{max-width:440px;text-align:center;padding:40px 32px;background:#12141c;
border:1px solid #1f2430;border-radius:16px}}
.badge{{width:64px;height:64px;border-radius:50%;background:{color}22;color:{color};
display:flex;align-items:center;justify-content:center;font-size:32px;margin:0 auto 20px}}
h1{{font-size:20px;margin:0 0 10px}} p{{color:#94a3b8;line-height:1.5;margin:0}}
</style></head><body><div class="card"><div class="badge">{icon}</div>
<h1>{title}</h1><p>{message}</p></div></body></html>"""


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
        return HTMLResponse(
            _callback_page("Connection failed", tokens["error"], ok=False),
            status_code=400,
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token", "")
    expires_in = int(tokens.get("expires_in", 3600))
    scope = tokens.get("scope", "")

    # Fetch the authenticated channel so we can persist a real, active Channel.
    info = await YouTubeClient(access_token).get_my_channel()
    if not info or not info.get("channel_id"):
        return HTMLResponse(
            _callback_page(
                "No channel found",
                "Signed in with Google, but this account has no YouTube channel. "
                "Create a channel and try again.",
                ok=False,
            ),
            status_code=400,
        )

    # Upsert the channel by its YouTube ID.
    result = await db.execute(
        select(Channel).where(Channel.youtube_channel_id == info["channel_id"])
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        channel = Channel(youtube_channel_id=info["channel_id"])
        db.add(channel)
    channel.title = info.get("title") or "YouTube Channel"
    channel.description = info.get("description")
    channel.custom_url = info.get("custom_url")
    channel.thumbnail_url = info.get("thumbnail_url")
    channel.subscriber_count = info.get("subscriber_count", 0)
    channel.video_count = info.get("video_count", 0)
    channel.view_count = info.get("view_count", 0)
    channel.is_active = True
    await db.flush()  # assign channel.id for the connection FK

    # Upsert the encrypted token record for this channel.
    result = await db.execute(
        select(YouTubeConnection).where(YouTubeConnection.channel_id == channel.id)
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        conn = YouTubeConnection(channel_id=channel.id)
        db.add(conn)
    conn.access_token_encrypted = security.encrypt_secret(access_token)
    # Google only returns a refresh_token on first consent — keep the old one otherwise.
    if refresh_token:
        conn.refresh_token_encrypted = security.encrypt_secret(refresh_token)
    elif not conn.refresh_token_encrypted:
        conn.refresh_token_encrypted = ""
    conn.token_uri = "https://oauth2.googleapis.com/token"
    conn.client_id = settings.GOOGLE_CLIENT_ID
    conn.scopes = scope.split() if scope else []
    conn.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    conn.is_valid = True
    conn.last_error = None

    await db.commit()
    upload_logger.info(f"YouTube channel connected: {channel.title} ({channel.youtube_channel_id})")

    return HTMLResponse(
        _callback_page(
            "YouTube connected",
            f"Connected to “{channel.title}”. You can close this tab and "
            f"return to YT Automation Studio.",
            ok=True,
        )
    )


@router.post("/disconnect")
async def disconnect_channel(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Channel))
    channels = q.scalars().all()
    for ch in channels:
        ch.is_active = False
    await db.commit()
    return {"success": True, "message": "YouTube disconnected."}
