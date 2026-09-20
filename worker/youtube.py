"""Upload a video to YouTube via the resumable upload protocol.

Uses the same Google access token as Drive (the stored grant covers both). The
upload is a single resumable PUT — fine for the worker, which handles one video
at a time and retries the whole item on failure.
"""
import os
from typing import Any, Dict, List

import httpx

from google_auth import get_access_token

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


def get_my_channel() -> Dict[str, Any]:
    token = get_access_token()
    resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet,statistics", "mine": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return {}
    ch = items[0]
    return {
        "channel_id": ch.get("id"),
        "title": ch.get("snippet", {}).get("title"),
    }


def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: str = "private",
    category_id: str = "22",
    publish_at: str = None,
) -> Dict[str, Any]:
    """Upload one video. Returns {video_id, url} or raises on failure.

    If publish_at (RFC3339 UTC) is given, the video is uploaded private and
    YouTube automatically makes it PUBLIC at that time (native scheduling).
    """
    token = get_access_token()
    file_size = os.path.getsize(file_path)

    status: Dict[str, Any] = {"selfDeclaredMadeForKids": False}
    if publish_at:
        # Scheduled publishing requires privacyStatus=private + publishAt.
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = privacy_status

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": (description or "")[:5000],
            "tags": tags[:50],
            "categoryId": category_id,
        },
        "status": status,
    }

    # 1. Open a resumable session.
    init = httpx.post(
        UPLOAD_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/*",
        },
        json=metadata,
        timeout=60.0,
    )
    if init.status_code != 200:
        raise RuntimeError(f"YouTube session init failed ({init.status_code}): {init.text}")
    session_url = init.headers.get("Location")
    if not session_url:
        raise RuntimeError("YouTube did not return an upload session URL")

    # 2. Upload the bytes.
    with open(file_path, "rb") as f:
        put = httpx.put(
            session_url,
            headers={"Content-Type": "video/*", "Content-Length": str(file_size)},
            content=f.read(),
            timeout=None,
        )
    if put.status_code not in (200, 201):
        raise RuntimeError(f"YouTube upload failed ({put.status_code}): {put.text}")

    video_id = put.json().get("id")
    return {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
