"""Multi-account management for YouTube uploads.

Each connected YouTube account is a row in Supabase `worker_credentials`, keyed
by its channel id, holding a refresh token encrypted with the SAME scheme the
cloud worker uses (Fernet from WORKER_SECRET_KEY). That's what lets the GitHub
Actions uploader post to any of your accounts with the laptop off.

Adding an account reuses the loopback OAuth flow that worker/authorize.py already
uses (redirect to http://localhost:8765/), so no new Google redirect URIs are
needed. The desktop UI opens the consent URL; a one-shot local server here
catches the code, exchanges it, and stores the grant.
"""
import base64
import hashlib
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

import httpx
from cryptography.fernet import Fernet
from supabase import create_client, Client

from app.core.config import settings
from app.core.logging import system_logger

_REDIRECT_PORT = 8765
_REDIRECT_URI = f"http://localhost:{_REDIRECT_PORT}/"
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

_lock = threading.Lock()
_connect: Dict[str, Any] = {"state": "idle", "message": "", "account": None}


_db_client: Optional[Client] = None


def _client() -> Optional[Client]:
    global _db_client
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        return None
    if _db_client is None:
        _db_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _db_client


def _cipher() -> Fernet:
    key_bytes = hashlib.sha256(settings.WORKER_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_accounts() -> List[Dict[str, Any]]:
    """Every connected YouTube account (excludes the Drive grant)."""
    db = _client()
    if db is None:
        return []
    try:
        rows = db.table("worker_credentials").select(
            "id,youtube_channel_id,youtube_channel_title,updated_at"
        ).neq("id", "drive").execute().data or []
    except Exception as e:
        system_logger.warning(f"accounts list failed: {e}")
        return []

    accounts, seen = [], set()
    for r in rows:
        ch = r.get("youtube_channel_id")
        # Collapse the legacy 'google' row into its channel if duplicated.
        key = ch or r["id"]
        if key in seen:
            continue
        seen.add(key)
        accounts.append({
            "id": r["id"],
            "channel_id": ch,
            "title": r.get("youtube_channel_title") or ("Primary account" if r["id"] == "google" else r["id"]),
            "is_primary": r["id"] == "google",
        })
    return accounts


def remove_account(account_id: str) -> bool:
    if account_id == "drive":
        return False
    db = _client()
    if db is None:
        return False
    try:
        db.table("worker_credentials").delete().eq("id", account_id).execute()
        return True
    except Exception as e:
        system_logger.error(f"accounts remove failed: {e}")
        return False


def _save_account(refresh_token: str, channel_id: str, channel_title: str) -> None:
    db = _client()
    if db is None:
        raise RuntimeError("Supabase not configured")
    db.table("worker_credentials").upsert({
        "id": channel_id,
        "refresh_token_encrypted": _cipher().encrypt(refresh_token.encode()).decode(),
        "scopes": _SCOPES,
        "youtube_channel_id": channel_id,
        "youtube_channel_title": channel_title,
        "updated_at": _now(),
    }).execute()


def _run_oauth_catcher() -> None:
    """One-shot local server: catch the OAuth code, exchange, store the account."""
    code_holder = {"code": None}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if params.get("code"):
                code_holder["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            ok = bool(code_holder["code"])
            msg = ("Account connected. You can close this tab and return to the app."
                   if ok else "Waiting for authorization…")
            self.wfile.write(f"<html><body style='font-family:sans-serif;background:#0b0d13;color:#e2e8f0'>"
                             f"<h2 style='margin:40px'>{msg}</h2></body></html>".encode())

        def log_message(self, *a):
            pass

    try:
        server = HTTPServer(("127.0.0.1", _REDIRECT_PORT), _Handler)
    except OSError as e:
        _connect.update(state="error", message=f"Port {_REDIRECT_PORT} busy — close other auth windows and retry ({e}).")
        return
    server.timeout = 2

    deadline = time.time() + 180  # give the user 3 minutes to consent
    try:
        while code_holder["code"] is None and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if not code_holder["code"]:
        _connect.update(state="error", message="Timed out waiting for Google sign-in.")
        return

    try:
        tok = httpx.post("https://oauth2.googleapis.com/token", data={
            "code": code_holder["code"],
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _REDIRECT_URI,
            "grant_type": "authorization_code",
        }, timeout=30.0)
        tok.raise_for_status()
        tokens = tok.json()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            _connect.update(state="error", message=(
                "Google didn't return a refresh token. Remove this app at "
                "myaccount.google.com/permissions and try again."))
            return

        ch = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=30.0,
        ).json().get("items", [])
        if not ch:
            _connect.update(state="error", message="That Google account has no YouTube channel.")
            return
        channel_id = ch[0]["id"]
        channel_title = ch[0].get("snippet", {}).get("title") or channel_id

        _save_account(refresh_token, channel_id, channel_title)
        _connect.update(state="connected", message=f"Connected {channel_title}",
                        account={"id": channel_id, "title": channel_title})
        system_logger.info(f"YouTube account connected for uploads: {channel_title} ({channel_id})")
    except Exception as e:  # noqa: BLE001
        _connect.update(state="error", message=f"Could not connect account: {e}")


def start_connect() -> Dict[str, Any]:
    """Begin an add-account flow; returns the Google consent URL to open."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        return {"error": "Google OAuth isn't configured (GOOGLE_CLIENT_ID/SECRET)."}
    with _lock:
        if _connect["state"] == "pending":
            return {"error": "An account connection is already in progress."}
        _connect.update(state="pending", message="Waiting for Google sign-in…", account=None)
    threading.Thread(target=_run_oauth_catcher, daemon=True, name="yt-account-oauth").start()

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent select_account",
    })
    return {"auth_url": auth_url}


def get_connect_status() -> Dict[str, Any]:
    return dict(_connect)
