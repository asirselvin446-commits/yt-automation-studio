"""Laptop-side push — run this while your laptop is on.

For each new video in your custom folder it:
  1. hashes it (so the same video is never queued twice),
  2. uploads it to Supabase Storage,
  3. inserts a QUEUED row in Supabase,
  4. (optionally) pings GitHub Actions to upload it right away.

It also does cleanup: any video that GitHub Actions has since uploaded to YouTube
gets its local file deleted (the Supabase copy is deleted by the uploader itself).

Run it once, or on a schedule (Windows Task Scheduler), or leave it looping with
  python push_local.py --loop
"""
import argparse
import hashlib
import mimetypes
import os
import sys
import time

import httpx

# Load a local .env so you don't have to export everything by hand.
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
from store import store  # noqa: E402
import storage  # noqa: E402


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_video(name: str) -> bool:
    return name.lower().endswith(config.VIDEO_EXTENSIONS)


def _trigger_github() -> None:
    if not (config.GITHUB_TOKEN and config.GITHUB_REPO):
        return
    try:
        httpx.post(
            f"https://api.github.com/repos/{config.GITHUB_REPO}/dispatches",
            headers={
                "Authorization": f"Bearer {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={"event_type": "new-video"},
            timeout=30.0,
        )
        print("  -> pinged GitHub Actions", flush=True)
    except Exception as e:
        print(f"  -> GitHub trigger failed (cron will still catch it): {e}", flush=True)


def cleanup_uploaded() -> None:
    """Delete local files for videos already uploaded to YouTube."""
    for item in store.uploaded_pending_local_cleanup():
        lp = item.get("local_path")
        if lp and os.path.exists(lp):
            try:
                os.remove(lp)
                print(f"[cleanup] deleted local file: {lp}", flush=True)
            except OSError as e:
                print(f"[cleanup] could not delete {lp}: {e}", flush=True)
        store.update_item(item["id"], local_deleted=True)


def push_new() -> int:
    folder = config.LOCAL_WATCH_FOLDER
    if not os.path.isdir(folder):
        print(f"[warn] folder not found: {folder}", flush=True)
        return 0

    queued = 0
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not (os.path.isfile(path) and _is_video(name)):
            continue

        digest = _sha256(path)
        if store.get_item_by_sha(digest):
            continue  # already known (queued, uploading, uploaded, or failed)

        storage_path = f"{digest[:12]}/{name}"
        print(f"[push] uploading {name} to Supabase Storage ...", flush=True)
        mime = mimetypes.guess_type(name)[0] or "video/mp4"
        storage.upload(path, storage_path, content_type=mime)
        store.enqueue({
            "file_name": name,
            "local_path": path,
            "storage_path": storage_path,
            "mime_type": mime,
            "size_bytes": os.path.getsize(path),
            "sha256": digest,
        })
        queued += 1
        print(f"[push] queued {name}", flush=True)

    if queued:
        _trigger_github()
    return queued


def run_once() -> None:
    cleanup_uploaded()
    n = push_new()
    print(f"Done. Queued {n} new video(s).", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="keep watching the folder")
    parser.add_argument("--interval", type=int, default=30, help="seconds between scans in --loop")
    args = parser.parse_args()

    missing = config.missing_for_push()
    if missing:
        print(f"[fatal] missing required env: {', '.join(missing)}", flush=True)
        raise SystemExit(1)

    print(f"Watching folder: {config.LOCAL_WATCH_FOLDER}", flush=True)
    if args.loop:
        while True:
            try:
                run_once()
            except Exception as e:  # noqa: BLE001
                print(f"[loop error] {e}", flush=True)
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
