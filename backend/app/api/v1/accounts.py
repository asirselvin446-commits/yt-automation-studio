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


@router.post("/folders")
async def set_folder_mapping(payload: FolderMapDTO):
    """Map an Auto-Upload folder to a YouTube account."""
    path = (payload.path or "").strip()
    if not path or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Folder does not exist.")
    if not payload.account_id:
        raise HTTPException(status_code=400, detail="Pick an account for this folder.")

    mappings: List[dict] = user_settings.get("folder_accounts", []) or []
    mappings = [m for m in mappings if m.get("path") != path]  # replace existing
    mappings.append({
        "path": path,
        "account_id": payload.account_id,
        "account_title": payload.account_title or payload.account_id,
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
