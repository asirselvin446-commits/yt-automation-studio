import os
import httpx
from typing import Dict, Any, Optional
from app.core.logging import upload_logger


class YouTubeClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    async def get_my_channel(self) -> Optional[Dict[str, Any]]:
        """Retrieve the primary connected channel info from YouTube Data API."""
        url = f"{self.base_url}/channels?part=snippet,statistics,brandingSettings&mine=true"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    ch = items[0]
                    snippet = ch.get("snippet", {})
                    stats = ch.get("statistics", {})
                    return {
                        "channel_id": ch.get("id"),
                        "title": snippet.get("title"),
                        "description": snippet.get("description"),
                        "custom_url": snippet.get("customUrl"),
                        "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                        "subscriber_count": int(stats.get("subscriberCount", 0)),
                        "video_count": int(stats.get("videoCount", 0)),
                        "view_count": int(stats.get("viewCount", 0)),
                    }
            upload_logger.error(f"Failed to fetch YouTube channel: {resp.text}")
            return None

    async def upload_video_resumable(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list,
        category_id: str = "28",  # Science & Tech
        privacy_status: str = "private",
        progress_callback=None
    ) -> Dict[str, Any]:
        """Upload video via YouTube Resumable Upload protocol."""
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        file_size = os.path.getsize(file_path)

        # 1. Initiate resumable upload session
        init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        metadata = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:50],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/*"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            init_resp = await client.post(init_url, headers=headers, json=metadata)
            if init_resp.status_code != 200:
                upload_logger.error(f"Resumable session init failed: {init_resp.text}")
                return {"error": f"Session init failed: {init_resp.text}"}

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                return {"error": "Upload URL not returned by YouTube"}

            # 2. Stream / upload video chunks
            with open(file_path, "rb") as f:
                upload_headers = {
                    "Content-Type": "video/*",
                    "Content-Length": str(file_size)
                }
                upload_resp = await client.put(upload_url, headers=upload_headers, content=f.read())

            if upload_resp.status_code in [200, 201]:
                res_data = upload_resp.json()
                video_id = res_data.get("id")
                return {
                    "success": True,
                    "video_id": video_id,
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                    "details": res_data
                }
            else:
                upload_logger.error(f"Upload failed: {upload_resp.text}")
                return {"error": f"Upload failed: {upload_resp.text}"}

    async def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Upload custom thumbnail for a video."""
        if not os.path.exists(thumbnail_path):
            return False

        url = f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "image/jpeg"
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(thumbnail_path, "rb") as img:
                resp = await client.post(url, headers=headers, content=img.read())
                return resp.status_code == 200
