"""Google Drive as the transient store for raw video bytes.

Supabase free tier caps uploads at 50 MB, which real videos exceed, so the bytes
live briefly in Drive instead (15 GB free, no practical per-file limit). Uses the
same Google grant as YouTube (drive.file scope), so no extra credentials. Files
are app-created and deleted right after the YouTube upload.
"""
import json
from typing import Optional

import httpx

from google_auth import get_access_token

UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
FILES_URL = "https://www.googleapis.com/drive/v3/files"


def upload(local_path: str, name: str, mime_type: str = "video/mp4") -> str:
    """Resumable-upload a local file to Drive. Returns the Drive file id."""
    import os

    token = get_access_token("drive")
    size = os.path.getsize(local_path)

    # 1. Start a resumable session with metadata.
    init = httpx.post(
        UPLOAD_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(size),
        },
        content=json.dumps({"name": name}),
        timeout=60.0,
    )
    if init.status_code not in (200, 201):
        raise RuntimeError(f"Drive session init failed ({init.status_code}): {init.text}")
    session_url = init.headers.get("Location")
    if not session_url:
        raise RuntimeError("Drive did not return an upload session URL")

    # 2. Upload the bytes.
    with open(local_path, "rb") as f:
        put = httpx.put(
            session_url,
            headers={"Content-Type": mime_type, "Content-Length": str(size)},
            content=f.read(),
            timeout=None,
        )
    if put.status_code not in (200, 201):
        raise RuntimeError(f"Drive upload failed ({put.status_code}): {put.text}")
    file_id = put.json().get("id")
    if not file_id:
        raise RuntimeError(f"Drive upload returned no file id: {put.text}")
    return file_id


def download(file_id: str, dest_path: str) -> str:
    """Stream a Drive file to dest_path. Returns dest_path."""
    import os

    token = get_access_token("drive")
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with httpx.stream(
        "GET",
        f"{FILES_URL}/{file_id}",
        params={"alt": "media", "supportsAllDrives": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=None,
    ) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
    return dest_path


def delete(file_id: str) -> None:
    """Delete a Drive file (safe to call more than once)."""
    try:
        token = get_access_token("drive")
        httpx.delete(
            f"{FILES_URL}/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"supportsAllDrives": "true"},
            timeout=30.0,
        )
    except Exception:
        pass
