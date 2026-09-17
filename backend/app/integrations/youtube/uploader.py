"""
YouTube Resumable Video Uploader — Implements chunked resumable uploads
to YouTube using the YouTube Data API v3 resumable upload protocol.
Supports exponential backoff, progress tracking, and upload resumption.
"""
import os
import json
import asyncio
import math
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import httpx
from app.core.logging import system_logger


class YouTubeUploader:
    """Chunked resumable video uploader for YouTube Data API v3."""

    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks (YouTube minimum recommended)
    MAX_RETRIES = 7
    INITIAL_RETRY_DELAY = 1.0  # seconds

    def __init__(self, access_token: str):
        self.access_token = access_token

    async def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
        category_id: str = "22",  # "People & Blogs" default
        privacy_status: str = "private",
        scheduled_publish_at: Optional[str] = None,
        playlist_id: Optional[str] = None,
        on_progress: Optional[Callable[[int, int, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a video file to YouTube using resumable upload.

        Args:
            file_path: Absolute path to the video file.
            title: Video title (max 100 chars).
            description: Video description (max 5000 chars).
            tags: List of tags.
            category_id: YouTube category ID.
            privacy_status: 'private', 'unlisted', or 'public'.
            scheduled_publish_at: ISO 8601 datetime for scheduled publishing.
            playlist_id: Optional playlist to add the video to.
            on_progress: Callback(bytes_sent, total_bytes, percentage).

        Returns:
            Dict with 'video_id', 'status', and full YouTube API response.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        file_size = path.stat().st_size
        mime_type = self._get_mime_type(path.suffix)

        system_logger.info(
            f"Starting YouTube upload: {path.name} ({file_size / (1024*1024):.1f} MB, {privacy_status})"
        )

        # Step 1: Initialize resumable upload session
        upload_uri = await self._init_resumable_upload(
            title=title,
            description=description,
            tags=tags or [],
            category_id=category_id,
            privacy_status=privacy_status,
            scheduled_publish_at=scheduled_publish_at,
            file_size=file_size,
            mime_type=mime_type,
        )

        if not upload_uri:
            return {"error": "Failed to initialize upload session", "status": "FAILED"}

        # Step 2: Upload file in chunks
        result = await self._upload_chunks(
            upload_uri=upload_uri,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            on_progress=on_progress,
        )

        if result.get("error"):
            system_logger.error(f"Upload failed: {result['error']}")
            return result

        video_id = result.get("id", "")
        system_logger.info(f"Upload complete! Video ID: {video_id}")

        # Step 3: Optionally add to playlist
        if playlist_id and video_id:
            await self._add_to_playlist(video_id, playlist_id)

        return {
            "video_id": video_id,
            "status": "UPLOADED",
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
            "response": result,
        }

    async def _init_resumable_upload(
        self,
        title: str,
        description: str,
        tags: list,
        category_id: str,
        privacy_status: str,
        scheduled_publish_at: Optional[str],
        file_size: int,
        mime_type: str,
    ) -> Optional[str]:
        """Initialize a resumable upload session and return the upload URI."""
        metadata = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        if scheduled_publish_at and privacy_status == "private":
            metadata["status"]["publishAt"] = scheduled_publish_at
            metadata["status"]["privacyStatus"] = "private"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(file_size),
        }

        params = {
            "uploadType": "resumable",
            "part": "snippet,status",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    self.UPLOAD_URL,
                    params=params,
                    headers=headers,
                    json=metadata,
                )

                if resp.status_code == 200:
                    upload_uri = resp.headers.get("Location")
                    if upload_uri:
                        system_logger.info("Resumable upload session initialized")
                        return upload_uri
                    system_logger.error("No Location header in upload init response")
                else:
                    system_logger.error(
                        f"Upload init failed ({resp.status_code}): {resp.text}"
                    )
                return None

            except Exception as e:
                system_logger.error(f"Upload init request failed: {e}")
                return None

    async def _upload_chunks(
        self,
        upload_uri: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Upload the file in chunks with exponential backoff retry."""
        bytes_sent = 0
        total_chunks = math.ceil(file_size / self.CHUNK_SIZE)

        with open(file_path, "rb") as f:
            chunk_number = 0
            while bytes_sent < file_size:
                chunk_number += 1
                chunk_start = bytes_sent
                chunk_end = min(bytes_sent + self.CHUNK_SIZE, file_size) - 1
                chunk_data = f.read(self.CHUNK_SIZE)
                actual_chunk_size = len(chunk_data)

                if actual_chunk_size == 0:
                    break

                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": mime_type,
                    "Content-Length": str(actual_chunk_size),
                    "Content-Range": f"bytes {chunk_start}-{chunk_end}/{file_size}",
                }

                # Retry with exponential backoff
                result = await self._upload_chunk_with_retry(
                    upload_uri, chunk_data, headers, chunk_number, total_chunks
                )

                if result is None:
                    return {"error": f"Chunk {chunk_number} failed after {self.MAX_RETRIES} retries"}

                bytes_sent += actual_chunk_size
                percentage = (bytes_sent / file_size) * 100

                system_logger.debug(
                    f"Chunk {chunk_number}/{total_chunks}: "
                    f"{bytes_sent / (1024*1024):.1f}/{file_size / (1024*1024):.1f} MB "
                    f"({percentage:.1f}%)"
                )

                if on_progress:
                    on_progress(bytes_sent, file_size, percentage)

                # If YouTube returned 200/201 (upload complete), return the response
                if isinstance(result, dict) and result.get("id"):
                    return result

        return {"error": "Upload completed but no video ID returned"}

    async def _upload_chunk_with_retry(
        self, upload_uri: str, chunk_data: bytes, headers: dict,
        chunk_number: int, total_chunks: int
    ) -> Optional[Any]:
        """Upload a single chunk with exponential backoff."""
        delay = self.INITIAL_RETRY_DELAY

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.put(upload_uri, content=chunk_data, headers=headers)

                    if resp.status_code in (200, 201):
                        # Upload complete
                        return resp.json()
                    elif resp.status_code == 308:
                        # Resume incomplete (chunk accepted, more to go)
                        return True
                    elif resp.status_code in (500, 502, 503, 504):
                        # Server error - retry
                        system_logger.warning(
                            f"Chunk {chunk_number} server error ({resp.status_code}), "
                            f"retry {attempt + 1}/{self.MAX_RETRIES} in {delay:.1f}s"
                        )
                    elif resp.status_code == 403:
                        system_logger.error(f"Upload forbidden: {resp.text}")
                        return None
                    elif resp.status_code == 404:
                        system_logger.error("Upload session expired")
                        return None
                    else:
                        system_logger.warning(
                            f"Chunk {chunk_number} unexpected status {resp.status_code}: {resp.text}"
                        )

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                system_logger.warning(
                    f"Chunk {chunk_number} network error: {e}, "
                    f"retry {attempt + 1}/{self.MAX_RETRIES} in {delay:.1f}s"
                )

            await asyncio.sleep(delay)
            delay = min(delay * 2, 64)  # Cap at 64 seconds

        return None

    async def _add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Add an uploaded video to a YouTube playlist."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://www.googleapis.com/youtube/v3/playlistItems",
                    params={"part": "snippet"},
                    headers=headers,
                    json=body,
                )
                if resp.status_code == 200:
                    system_logger.info(f"Video {video_id} added to playlist {playlist_id}")
                    return True
                else:
                    system_logger.warning(
                        f"Playlist add failed ({resp.status_code}): {resp.text}"
                    )
            except Exception as e:
                system_logger.error(f"Playlist add error: {e}")
        return False

    async def check_upload_status(self, upload_uri: str) -> Dict[str, Any]:
        """Check the status of an in-progress resumable upload."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Range": "bytes */*",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.put(upload_uri, headers=headers, content=b"")
                if resp.status_code in (200, 201):
                    return {"status": "COMPLETE", "response": resp.json()}
                elif resp.status_code == 308:
                    range_header = resp.headers.get("Range", "")
                    return {"status": "IN_PROGRESS", "range": range_header}
                else:
                    return {"status": "UNKNOWN", "code": resp.status_code}
            except Exception as e:
                return {"status": "ERROR", "error": str(e)}

    @staticmethod
    def _get_mime_type(extension: str) -> str:
        """Map file extension to MIME type."""
        mime_map = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska",
            ".avi": "video/x-msvideo",
            ".webm": "video/webm",
            ".flv": "video/x-flv",
            ".wmv": "video/x-ms-wmv",
        }
        return mime_map.get(extension.lower(), "video/mp4")
