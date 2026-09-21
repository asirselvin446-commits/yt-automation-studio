"""Multi-account management: connect/list/remove YouTube accounts, and map each
Auto-Upload folder to the account its videos should upload to."""
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import user_settings
from app.services import accounts
from app.services import supabase_ingest_service

router = APIRouter(prefix="/accounts", tags=["YouTube Accounts"])


@router.get("")
async def list_accounts():
    return {
        "accounts": accounts.list_accounts(),
        "folders": user_settings.get("folder_accounts", []) or [],
        "connect": accounts.get_connect_status(),
    }


@router.post("/connect")
async def connect_account():
    """Start an add-account OAuth flow; the UI opens the returned URL."""
    res = accounts.start_connect()
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/connect-status")
async def connect_status():
    return accounts.get_connect_status()


@router.delete("/{account_id}")
async def remove_account(account_id: str):
    ok = accounts.remove_account(account_id)
    # Drop any folder mappings that pointed at the removed account.
    mappings = user_settings.get("folder_accounts", []) or []
    mappings = [m for m in mappings if m.get("account_id") != account_id]
    user_settings.set_value("folder_accounts", mappings)
    return {"success": ok}


class FolderMapDTO(BaseModel):
    path: str
    account_id: str
    account_title: Optional[str] = None
    visibility: Optional[str] = None            # public | unlisted | private
    schedule_per_day: Optional[int] = None      # 0 = immediate, else N/day
    publish_mode: Optional[str] = None          # auto | review


@router.post("/folders")
async def set_folder_mapping(payload: FolderMapDTO):
    """Create or update a folder→account link, with per-folder upload settings."""
    path = (payload.path or "").strip()
    if not path or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Folder does not exist.")
    if not payload.account_id:
        raise HTTPException(status_code=400, detail="Pick an account for this folder.")

    mappings: List[dict] = user_settings.get("folder_accounts", []) or []
    existing = next((m for m in mappings if m.get("path") == path), {})
    mappings = [m for m in mappings if m.get("path") != path]  # replace existing

    def _pick(new, old, default):
        return new if new is not None else old if old is not None else default

    vis = _pick(payload.visibility, existing.get("visibility"), "public")
    if vis not in ("public", "unlisted", "private"):
        vis = "public"
    mode = _pick(payload.publish_mode, existing.get("publish_mode"), "auto")
    if mode not in ("auto", "review"):
        mode = "auto"
    per_day = max(0, min(8, int(_pick(payload.schedule_per_day, existing.get("schedule_per_day"), 0))))

    mappings.append({
        "path": path,
        "account_id": payload.account_id,
        "account_title": payload.account_title or existing.get("account_title") or payload.account_id,
        "visibility": vis,
        "schedule_per_day": per_day,
        "publish_mode": mode,
    })
    user_settings.set_value("folder_accounts", mappings)
    # Kick an immediate scan so new files start flowing right away.
    status = supabase_ingest_service.run_once()
    return {"success": True, "folders": mappings, "upload_status": status}


class FolderDelDTO(BaseModel):
    path: str


@router.post("/folders/remove")
async def remove_folder_mapping(payload: FolderDelDTO):
    mappings = user_settings.get("folder_accounts", []) or []
    mappings = [m for m in mappings if m.get("path") != (payload.path or "").strip()]
    user_settings.set_value("folder_accounts", mappings)
    return {"success": True, "folders": mappings}
