"""Supabase Storage helpers — the transient home for raw video bytes.

The laptop uploads a video here; GitHub Actions downloads it, uploads it to
YouTube, then removes it. So objects here are short-lived by design.
"""
import os
from typing import Optional

from config import config
from store import store

_bucket_ready = False


def ensure_bucket() -> None:
    """Create the storage bucket if it doesn't exist (idempotent)."""
    global _bucket_ready
    if _bucket_ready:
        return
    try:
        existing = {b.name for b in store.db.storage.list_buckets()}
    except Exception:
        existing = set()
    if config.STORAGE_BUCKET not in existing:
        try:
            # Private bucket — objects are only reachable with the service key.
            store.db.storage.create_bucket(config.STORAGE_BUCKET, options={"public": False})
        except Exception:
            # Race or already-exists: ignore; upload will surface real problems.
            pass
    _bucket_ready = True


def upload(local_path: str, storage_path: str, content_type: Optional[str] = None) -> str:
    """Upload a local file to the bucket at storage_path. Returns storage_path."""
    ensure_bucket()
    with open(local_path, "rb") as f:
        store.db.storage.from_(config.STORAGE_BUCKET).upload(
            storage_path,
            f.read(),
            {"content-type": content_type or "video/mp4", "upsert": "true"},
        )
    return storage_path


def download(storage_path: str, dest_path: str) -> str:
    """Download an object from the bucket to dest_path. Returns dest_path."""
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    data = store.db.storage.from_(config.STORAGE_BUCKET).download(storage_path)
    with open(dest_path, "wb") as f:
        f.write(data)
    return dest_path


def remove(storage_path: str) -> None:
    """Delete an object from the bucket (safe to call more than once)."""
    try:
        store.db.storage.from_(config.STORAGE_BUCKET).remove([storage_path])
    except Exception:
        pass
