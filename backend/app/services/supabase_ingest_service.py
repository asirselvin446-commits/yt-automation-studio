"""Push videos from the user's chosen folder up to Supabase for cloud upload.

Runs in a background thread while the desktop app is open. For each new video in
the custom folder it uploads the bytes to Supabase Storage and inserts a QUEUED
row in `ingest_items`; GitHub Actions then uploads to YouTube and clears the
storage object. When an item is UPLOADED, we delete the local file too.

This is the laptop-side half of the "laptop can be off" pipeline, integrated so
the folder is chosen in the app instead of a .env file.
"""
import base64
import hashlib
import json
import mimetypes
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from cryptography.fernet import Fernet
from supabase import create_client, Client

from app.core.config import settings
from app.core import user_settings
from app.core.logging import system_logger

DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv")
_POLL_SECONDS = 30

_status: Dict[str, Any] = {
    "running": False,
    "folder": None,
    "last_run": None,
    "last_error": None,
    "queued": 0,
    "uploaded": 0,
    "failed": 0,
}
_started = False
_lock = threading.Lock()


def _client() -> Optional[Client]:
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _drive_access_token(db: Client) -> str:
    """Mint a Drive access token from the refresh token the worker stored."""
    res = db.table("worker_credentials").select("*").eq("id", "drive").limit(1).execute()
    rows = res.data or []
    if not rows or not rows[0].get("refresh_token_encrypted"):
        raise RuntimeError("No Drive credentials — run 'authorize.py --service drive' once.")
    key_bytes = hashlib.sha256(settings.WORKER_SECRET_KEY.encode()).digest()
    refresh_token = Fernet(base64.urlsafe_b64encode(key_bytes)).decrypt(
        rows[0]["refresh_token_encrypted"].encode()
    ).decode()
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Drive token refresh failed ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


def _drive_upload(token: str, local_path: str, name: str, mime: str) -> str:
    """Resumable-upload a file to Drive; return the Drive file id."""
    size = os.path.getsize(local_path)
    init = httpx.post(
        DRIVE_UPLOAD_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(size),
        },
        content=json.dumps({"name": name}),
        timeout=60.0,
    )
    if init.status_code not in (200, 201):
        raise RuntimeError(f"Drive session init failed ({init.status_code}): {init.text}")
    session_url = init.headers["Location"]
    with open(local_path, "rb") as f:
        put = httpx.put(
            session_url,
            headers={"Content-Type": mime, "Content-Length": str(size)},
            content=f.read(),
            timeout=None,
        )
    if put.status_code not in (200, 201):
        raise RuntimeError(f"Drive upload failed ({put.status_code}): {put.text}")
    return put.json()["id"]


def _cleanup_uploaded(db: Client) -> None:
    """Delete local files for videos already uploaded to YouTube."""
    res = (
        db.table("ingest_items")
        .select("id,local_path")
        .eq("status", "UPLOADED")
        .eq("local_deleted", False)
        .execute()
    )
    for item in res.data or []:
        lp = item.get("local_path")
        if lp and os.path.exists(lp):
            try:
                os.remove(lp)
                system_logger.info(f"Ingest cleanup: removed local file {lp}")
            except OSError as e:
                system_logger.warning(f"Ingest cleanup failed for {lp}: {e}")
        db.table("ingest_items").update(
            {"local_deleted": True, "updated_at": _now()}
        ).eq("id", item["id"]).execute()


def _push_new(db: Client, folder: str) -> int:
    # Only look up a Drive token if there's actually something new to upload.
    pending = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not (os.path.isfile(path) and name.lower().endswith(VIDEO_EXTENSIONS)):
            continue
        digest = _sha256(path)
        seen = db.table("ingest_items").select("id").eq("sha256", digest).limit(1).execute()
        if not seen.data:
            pending.append((name, path, digest))

    if not pending:
        return 0

    token = _drive_access_token(db)
    queued = 0
    for name, path, digest in pending:
        mime = mimetypes.guess_type(name)[0] or "video/mp4"
        system_logger.info(f"Ingest: uploading {name} to Google Drive")
        file_id = _drive_upload(token, path, name, mime)
        db.table("ingest_items").insert(
            {
                "file_name": name,
                "local_path": path,
                "storage_path": file_id,   # Drive file id
                "mime_type": mime,
                "size_bytes": os.path.getsize(path),
                "sha256": digest,
                "status": "QUEUED",
                "created_at": _now(),
                "updated_at": _now(),
            }
        ).execute()
        queued += 1
    return queued


def _refresh_counts(db: Client) -> None:
    try:
        rows = db.table("ingest_items").select("status").execute().data or []
        _status["queued"] = sum(1 for r in rows if r["status"] in ("QUEUED", "PROCESSING"))
        _status["uploaded"] = sum(1 for r in rows if r["status"] == "UPLOADED")
        _status["failed"] = sum(1 for r in rows if r["status"] == "FAILED")
    except Exception:
        pass


def run_once() -> Dict[str, Any]:
    """One scan+push+cleanup pass. Safe to call ad hoc (e.g. right after the user picks a folder)."""
    folder = user_settings.get("custom_upload_folder")
    _status["folder"] = folder
    _status["last_run"] = _now()
    if not folder or not os.path.isdir(folder):
        return _status
    db = _client()
    if db is None:
        _status["last_error"] = "Supabase not configured"
        return _status
    try:
        _cleanup_uploaded(db)
        _push_new(db, folder)
        _refresh_counts(db)
        _status["last_error"] = None
    except Exception as e:  # noqa: BLE001
        _status["last_error"] = str(e)[:300]
        system_logger.error(f"Ingest run error: {e}")
    return _status


def get_status() -> Dict[str, Any]:
    return dict(_status)


def _loop() -> None:
    while True:
        try:
            run_once()
        except Exception as e:  # noqa: BLE001
            system_logger.error(f"Ingest loop error: {e}")
        time.sleep(_POLL_SECONDS)


def start() -> None:
    """Start the background pusher once."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    _status["running"] = True
    threading.Thread(target=_loop, daemon=True, name="supabase-ingest").start()
    system_logger.info("Supabase ingest pusher started.")
