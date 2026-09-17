"""One-time Google authorization for the worker.

Run this ONCE on your own computer. It opens a browser, asks you to grant Drive
(read) + YouTube (upload) access, then stores the resulting refresh token
(encrypted) in Supabase. After that the Render worker can act as you forever,
refreshing its own access tokens — your laptop is no longer needed.

Usage (from the worker/ folder, with the same env values the worker will use):
    python authorize.py

It reads configuration from the environment, falling back to a local .env file
(worker/.env or ../.env) if present.
"""
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx


# --- load .env (so you don't have to export everything by hand) -------------
def _load_env():
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(here, ".env"), os.path.join(here, "..", ".env")):
        if os.path.exists(candidate):
            for line in open(candidate, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config  # noqa: E402
from crypto import encrypt  # noqa: E402
from store import store  # noqa: E402

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

_auth_code = {"code": None}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        _auth_code["code"] = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        ok = bool(_auth_code["code"])
        msg = "Authorization complete. You can close this tab." if ok else "Authorization failed."
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h2>{msg}</h2></body></html>".encode())

    def log_message(self, *args):  # silence server logs
        pass


def main():
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET") if not getattr(config, k)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        raise SystemExit(1)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": config.GOOGLE_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    print("Opening browser for Google authorization ...")
    print(f"If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _Handler)
    while _auth_code["code"] is None:
        server.handle_request()

    print("Exchanging authorization code for tokens ...")
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": _auth_code["code"],
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("No refresh token returned. Remove the app's access at "
              "https://myaccount.google.com/permissions and run this again.")
        raise SystemExit(1)

    # Identify the channel this grant belongs to (nice to display later).
    channel_id = channel_title = None
    try:
        ch = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=30.0,
        ).json().get("items", [])
        if ch:
            channel_id = ch[0].get("id")
            channel_title = ch[0].get("snippet", {}).get("title")
    except Exception:
        pass

    store.save_google_credentials(
        refresh_token_encrypted=encrypt(refresh_token),
        scopes=SCOPES,
        channel_id=channel_id,
        channel_title=channel_title,
    )
    print(f"\n[OK] Stored Google credentials in Supabase for channel: {channel_title or '(unknown)'}")
    print("The GitHub Actions uploader can now run without your laptop.")


if __name__ == "__main__":
    main()
