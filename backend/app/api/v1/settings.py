import os
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
        "watch_folder_root": str(settings.root_path),
        "inbox_path": str(settings.inbox_path),
        "custom_upload_folder": user_settings.get("custom_upload_folder"),
        "upload_status": supabase_ingest_service.get_status(),
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
