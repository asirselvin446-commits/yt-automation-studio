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
