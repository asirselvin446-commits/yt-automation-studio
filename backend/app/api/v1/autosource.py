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
def get_autosource_status():
    return autosource.get_status()


class AutosourceConfigDTO(BaseModel):
    enabled: Optional[bool] = None
    niche: Optional[str] = None
    per_day: Optional[int] = None
    format: Optional[str] = None              # shorts | landscape
    provider: Optional[str] = None            # edge | fish
    voice: Optional[str] = None               # edge-tts voice id
    fish_api_key: Optional[str] = None        # optional; blank keeps existing
    fish_voice: Optional[str] = None
    eleven_api_key: Optional[str] = None      # optional; blank keeps existing
    eleven_voice: Optional[str] = None
    pexels_api_key: Optional[str] = None      # optional; blank keeps existing
    account_id: Optional[str] = None          # which YouTube account to post to
    post_time_utc: Optional[str] = None       # daily upload time as UTC "HH:MM" ('' = ASAP)
    music_enabled: Optional[bool] = None      # add a background music bed
    music_url: Optional[str] = None           # optional royalty-free track URL


@router.post("/config")
def set_autosource_config(payload: AutosourceConfigDTO):
    fields = {k: v for k, v in payload.dict().items() if v is not None}
    config = autosource.set_config(fields)
    return {"success": True, "config": config}


@router.post("/generate")
def generate_now():
    return autosource.generate_now()
