"""Push videos from the user's chosen folder up to Supabase for cloud upload.

Runs in a background thread while the desktop app is open. For each new video in
the custom folder it uploads the bytes to Supabase Storage and inserts a QUEUED
row in `ingest_items`; GitHub Actions then uploads to YouTube and clears the
storage object. When an item is UPLOADED, we delete the local file too.

This is the laptop-side half of the "laptop can be off" pipeline, integrated so
the folder is chosen in the app instead of a .env file.
"""
import hashlib
import mimetypes
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import create_client, Client

from app.core.config import settings
from app.core import user_settings
from app.core.logging import system_logger

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


def _ensure_bucket(db: Client) -> None:
    try:
        existing = {b.name for b in db.storage.list_buckets()}
        if settings.STORAGE_BUCKET not in existing:
            db.storage.create_bucket(settings.STORAGE_BUCKET, options={"public": False})
    except Exception:
        pass  # upload will surface any real problem


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
    queued = 0
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not (os.path.isfile(path) and name.lower().endswith(VIDEO_EXTENSIONS)):
            continue

        digest = _sha256(path)
        seen = db.table("ingest_items").select("id").eq("sha256", digest).limit(1).execute()
        if seen.data:
            continue

        storage_path = f"{digest[:12]}/{name}"
        mime = mimetypes.guess_type(name)[0] or "video/mp4"
        system_logger.info(f"Ingest: uploading {name} to Supabase Storage")
        with open(path, "rb") as f:
            db.storage.from_(settings.STORAGE_BUCKET).upload(
                storage_path, f.read(), {"content-type": mime, "upsert": "true"}
            )
        db.table("ingest_items").insert(
            {
                "file_name": name,
                "local_path": path,
                "storage_path": storage_path,
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
        _ensure_bucket(db)
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
