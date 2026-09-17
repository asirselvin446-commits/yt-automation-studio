"""Exchange stored refresh tokens for short-lived access tokens.

Google won't grant Drive and YouTube scopes in one consent, so there are two
separate grants in Supabase: "google" (YouTube) and "drive" (Drive). This mints
a valid access token for whichever service is asked, caching each with a margin.
"""
import time
from typing import Dict

import httpx

from config import config
from crypto import decrypt
from store import store

TOKEN_URI = "https://oauth2.googleapis.com/token"

# service name -> credential row id in worker_credentials
_SERVICE_TO_ID = {"youtube": "google", "drive": "drive"}
_cache: Dict[str, dict] = {}


def get_access_token(service: str = "youtube", force: bool = False) -> str:
    """Return a valid Google access token for the given service.

    service is "youtube" or "drive". Raises RuntimeError if that grant is
    missing (authorize.py not run for it) or the refresh fails.
    """
    cred_id = _SERVICE_TO_ID.get(service, service)
    now = time.time()
    cache = _cache.setdefault(cred_id, {"access_token": None, "expires_at": 0.0})
    if not force and cache["access_token"] and now < cache["expires_at"] - 60:
        return cache["access_token"]

    creds = store.get_google_credentials(cred_id)
    if not creds or not creds.get("refresh_token_encrypted"):
        raise RuntimeError(
            f"No '{service}' Google credentials in Supabase. Run "
            f"'python authorize.py --service {service}' once to grant access."
        )

    refresh_token = decrypt(creds["refresh_token_encrypted"])
    if not refresh_token:
        raise RuntimeError("Stored refresh token could not be decrypted — check WORKER_SECRET_KEY.")

    resp = httpx.post(
        TOKEN_URI,
        data={
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Google token refresh failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    cache["access_token"] = data["access_token"]
    cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return cache["access_token"]
