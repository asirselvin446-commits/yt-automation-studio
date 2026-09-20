import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core import user_settings
from app.schemas.dto import AISettingsUpdateDTO
from app.services import supabase_ingest_service

router = APIRouter(prefix="/settings", tags=["Studio Settings"])


@router.get("")
async def get_settings_status():
    return {
        "custom_upload_folder": user_settings.get("custom_upload_folder"),
        "publish_mode": user_settings.get("publish_mode", "auto"),
        "visibility": user_settings.get("visibility", "public"),
        "schedule_per_day": int(user_settings.get("schedule_per_day", 0) or 0),
        "upload_status": supabase_ingest_service.get_status(),
        "cloud_ingest_active": supabase_ingest_service.get_status().get("running", False),
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
        "default_ai_provider": settings.DEFAULT_AI_PROVIDER,
        "ai_cost_preset": settings.DEFAULT_AI_QUALITY_PRESET,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        "youtube_client_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "local_ai_url": settings.LOCAL_AI_BASE_URL
    }


class UploadFolderDTO(BaseModel):
    path: str


@router.post("/upload-folder")
async def set_upload_folder(payload: UploadFolderDTO):
    """Save the custom folder to auto-upload videos from, and push immediately."""
    path = (payload.path or "").strip()
    if not path or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Folder does not exist.")
    user_settings.set_value("custom_upload_folder", path)
    # Kick an immediate scan so the user sees it working right away.
    status = supabase_ingest_service.run_once()
    return {"success": True, "custom_upload_folder": path, "upload_status": status}


class PublishModeDTO(BaseModel):
    mode: str  # "auto" | "review"


@router.post("/publish-mode")
async def set_publish_mode(payload: PublishModeDTO):
    """Choose whether folder videos auto-publish or are held for review."""
    mode = (payload.mode or "auto").lower()
    if mode not in ("auto", "review"):
        raise HTTPException(status_code=400, detail="mode must be 'auto' or 'review'.")
    user_settings.set_value("publish_mode", mode)
    return {"success": True, "publish_mode": mode}


class PublishingDTO(BaseModel):
    visibility: Optional[str] = None       # public | unlisted | private
    schedule_per_day: Optional[int] = None  # 0 = publish immediately, else N/day


@router.post("/publishing")
async def set_publishing(payload: PublishingDTO):
    """Set default visibility and drip-schedule (videos per day)."""
    if payload.visibility is not None:
        v = payload.visibility.lower()
        if v not in ("public", "unlisted", "private"):
            raise HTTPException(status_code=400, detail="visibility must be public, unlisted, or private.")
        user_settings.set_value("visibility", v)
    if payload.schedule_per_day is not None:
        n = max(0, min(24, int(payload.schedule_per_day)))
        user_settings.set_value("schedule_per_day", n)
    return {
        "success": True,
        "visibility": user_settings.get("visibility", "public"),
        "schedule_per_day": int(user_settings.get("schedule_per_day", 0) or 0),
    }


@router.post("/publish-held")
async def publish_held(item_id: Optional[str] = None):
    """Release held video(s) to the cloud upload queue (Review mode approval)."""
    released = supabase_ingest_service.release_held(item_id)
    return {"success": True, "released": released, "upload_status": supabase_ingest_service.get_status()}


@router.post("/ai")
async def update_ai_settings(payload: AISettingsUpdateDTO):
    if payload.default_provider:
        settings.DEFAULT_AI_PROVIDER = payload.default_provider
    if payload.gemini_key:
        settings.GEMINI_API_KEY = payload.gemini_key
    if payload.openai_key:
        settings.OPENAI_API_KEY = payload.openai_key
    if payload.anthropic_key:
        settings.ANTHROPIC_API_KEY = payload.anthropic_key
    if payload.local_ai_url:
        settings.LOCAL_AI_BASE_URL = payload.local_ai_url
    if payload.ai_cost_preset:
        settings.DEFAULT_AI_QUALITY_PRESET = payload.ai_cost_preset

    return {"success": True, "message": "AI settings updated successfully."}
