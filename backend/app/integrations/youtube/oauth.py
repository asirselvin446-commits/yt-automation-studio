import urllib.parse
from typing import Dict, Any, Optional
import httpx
from app.core.config import settings
from app.core.security import security
from app.core.logging import upload_logger

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly"
]


class YouTubeOAuth:
    @staticmethod
    def get_authorization_url() -> Dict[str, str]:
        """Generate Google OAuth 2.0 consent URL."""
        if not settings.GOOGLE_CLIENT_ID:
            return {"error": "Google Client ID not configured in Settings"}

        state = security.generate_oauth_state()
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return {"url": auth_url, "state": state}

    @staticmethod
    async def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return {"error": "Google OAuth credentials not configured"}

        url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            if resp.status_code != 200:
                upload_logger.error(f"Failed to exchange OAuth code: {resp.text}")
                return {"error": f"OAuth exchange failed: {resp.text}"}
            return resp.json()

    @staticmethod
    async def refresh_access_token(refresh_token: str) -> Optional[str]:
        """Refresh an expired access token."""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            if resp.status_code == 200:
                return resp.json().get("access_token")
            return None


youtube_oauth = YouTubeOAuth()
