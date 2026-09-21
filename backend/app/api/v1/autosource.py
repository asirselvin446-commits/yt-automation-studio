"""Auto-Source engine control API.

Configure the cloud content engine (niche, frequency, voice), watch live run
status, and trigger an immediate generation. The actual video generation +
upload happens in GitHub Actions (24/7, laptop-independent).
"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.services import autosource

router = APIRouter(prefix="/autosource", tags=["Auto-Source Engine"])


@router.get("")
async def get_autosource_status():
    return autosource.get_status()


class AutosourceConfigDTO(BaseModel):
    enabled: Optional[bool] = None
    niche: Optional[str] = None
    per_day: Optional[int] = None
    provider: Optional[str] = None            # edge | fish
    voice: Optional[str] = None               # edge-tts voice id
    fish_api_key: Optional[str] = None        # optional; blank keeps existing
    fish_voice: Optional[str] = None


@router.post("/config")
async def set_autosource_config(payload: AutosourceConfigDTO):
    fields = {k: v for k, v in payload.dict().items() if v is not None}
    config = autosource.set_config(fields)
    return {"success": True, "config": config}


@router.post("/generate")
async def generate_now():
    return autosource.generate_now()
