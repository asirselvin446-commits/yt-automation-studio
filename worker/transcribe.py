"""Transcribe a video with Gemini multimodal (Files API).

Keeps the whole pipeline on a single AI key: the video is uploaded to the Gemini
Files API, we wait for it to become ACTIVE, then ask the model for a plain-text
transcript. No separate speech-to-text service, no ffmpeg audio extraction.
"""
import time

import httpx

from config import config

GENAI = "https://generativelanguage.googleapis.com"
_UPLOAD_TIMEOUT = None  # large files: no read timeout


def upload_to_gemini(file_path: str, mime_type: str, display_name: str, api_key: str = None) -> str:
    """Resumable-upload a media file; return its file resource name (files/xxx).

    Uploaded files are scoped to the key that uploaded them, so a caller that
    rotates keys must re-upload with the new key.
    """
    import os

    size = os.path.getsize(file_path)
    key = api_key or config.GEMINI_API_KEY

    # 1. Start a resumable session.
    start = httpx.post(
        f"{GENAI}/upload/v1beta/files?key={key}",
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        json={"file": {"display_name": display_name}},
        timeout=60.0,
    )
    start.raise_for_status()
    upload_url = start.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("Gemini did not return an upload URL")

    # 2. Upload the bytes and finalize.
    with open(file_path, "rb") as f:
        up = httpx.post(
            upload_url,
            headers={
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
                "Content-Length": str(size),
            },
            content=f.read(),
            timeout=_UPLOAD_TIMEOUT,
        )
    up.raise_for_status()
    file_info = up.json().get("file", {})
    name = file_info.get("name")
    if not name:
        raise RuntimeError(f"Gemini upload returned no file name: {up.text}")

    # 3. Wait until the file is processed (ACTIVE) before referencing it.
    deadline = time.time() + 600
    while time.time() < deadline:
        state = file_info.get("state")
        if state == "ACTIVE":
            return file_info.get("uri", name)
        if state == "FAILED":
            raise RuntimeError("Gemini failed to process the uploaded video")
        time.sleep(5)
        poll = httpx.get(f"{GENAI}/v1beta/{name}?key={key}", timeout=30.0)
        poll.raise_for_status()
        file_info = poll.json()
    raise RuntimeError("Timed out waiting for Gemini to process the video")


def transcribe(file_path: str, mime_type: str, display_name: str = "video") -> str:
    """Return a plain-text transcript of the video's spoken audio."""
    file_uri = upload_to_gemini(file_path, mime_type or "video/mp4", display_name)
    key = config.GEMINI_API_KEY
    prompt = (
        "Transcribe all spoken words in this video verbatim as plain text. "
        "Do not add commentary, timestamps, or speaker labels. If there is no "
        "speech, respond with an empty string."
    )
    resp = httpx.post(
        f"{GENAI}/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={key}",
        json={
            "contents": [
                {
                    "parts": [
                        {"file_data": {"mime_type": mime_type or "video/mp4", "file_uri": file_uri}},
                        {"text": prompt},
                    ]
                }
            ]
        },
        timeout=300.0,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
    return "".join(p.get("text", "") for p in parts).strip()
