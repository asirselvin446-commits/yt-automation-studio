"""Fetch real, license-clean stock video B-roll for each narration beat.

Uses the free Pexels Video API (one free key). Given a short search query, it
returns a downloaded portrait mp4 clip suitable for a Short. If no key is set or
nothing matches, the caller falls back to a generated AI image with Ken-Burns
motion, so the pipeline always produces something.

Pexels' license permits free commercial use and reuse, which — combined with the
original script, voiceover and edit — keeps the finished Short monetization-safe.
"""
import os
from typing import Optional

import httpx

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"


def _pick_portrait_file(video: dict, min_h: int = 1000) -> Optional[str]:
    """Choose the best portrait-ish mp4 rendition link from a Pexels video."""
    best = None
    best_h = 0
    for vf in video.get("video_files", []):
        if vf.get("file_type") != "video/mp4":
            continue
        w, h = vf.get("width") or 0, vf.get("height") or 0
        if not w or not h:
            continue
        portrait = h >= w
        # Prefer portrait; among those, the tallest up to ~1920.
        score_h = h if portrait else h // 3
        if score_h > best_h and h <= 2200:
            best_h = score_h
            best = vf.get("link")
    if best_h < min_h:
        # Nothing tall enough — still return the best we found (we crop anyway).
        return best
    return best


def fetch_clip(query: str, out_path: str, api_key: str, *, per_page: int = 8) -> Optional[str]:
    """Search Pexels for `query` and download a portrait clip to out_path.

    Returns the path on success, or None (so the caller uses the image fallback).
    """
    if not api_key:
        return None
    try:
        resp = httpx.get(
            PEXELS_VIDEO_SEARCH,
            params={"query": query, "per_page": per_page,
                    "orientation": "portrait", "size": "medium"},
            headers={"Authorization": api_key},
            timeout=30.0,
        )
        if resp.status_code != 200:
            print(f"[autosource-media] Pexels search {resp.status_code} for '{query}'", flush=True)
            return None
        videos = resp.json().get("videos", [])
        if not videos:
            return None
        link = None
        for v in videos:
            link = _pick_portrait_file(v)
            if link:
                break
        if not link:
            return None

        with httpx.stream("GET", link, timeout=120.0, follow_redirects=True) as r:
            if r.status_code != 200:
                return None
            with open(out_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        if os.path.getsize(out_path) > 10240:
            return out_path
        return None
    except Exception as e:  # noqa: BLE001 — any failure => image fallback
        print(f"[autosource-media] clip fetch failed for '{query}': {e}", flush=True)
        return None
