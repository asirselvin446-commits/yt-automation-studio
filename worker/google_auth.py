"""Exchange the stored refresh token for short-lived access tokens.

The one-time authorize.py grants Drive + YouTube scopes and stores the refresh
token (encrypted) in Supabase. Here the worker turns that into a fresh access
token whenever it needs to call Drive or YouTube. Access tokens last ~1 hour, so
we cache with a safety margin and refresh on demand.
"""
import time
from typing import Optional

import httpx

from config import config
from crypto import decrypt
from store import store

TOKEN_URI = "https://oauth2.googleapis.com/token"

_cache = {"access_token": None, "expires_at": 0.0}


def get_access_token(force: bool = False) -> str:
    """Return a valid Google access token, refreshing if needed.

    Raises RuntimeError if no credentials are stored (authorize.py not run yet)
    or the refresh fails (revoked / expired grant).
    """
    now = time.time()
    if not force and _cache["access_token"] and now < _cache["expires_at"] - 60:
        return _cache["access_token"]

    creds = store.get_google_credentials()
    if not creds or not creds.get("refresh_token_encrypted"):
        raise RuntimeError(
            "No Google credentials in Supabase. Run authorize.py once to grant "
            "Drive + YouTube access."
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
    _cache["access_token"] = data["access_token"]
    _cache["expires_at"] = now + int(data.get("expires_in", 3600))
    return _cache["access_token"]
