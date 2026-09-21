"""Keyless AI imagery for each narration beat.

Uses Pollinations' free image endpoint (no key, no signup) to turn each beat's
image prompt into an original 16:9 picture. If the service is unreachable, we
fall back to a generated gradient card so a run still produces a video.

Because every image is generated (not scraped from third parties), there is no
third-party copyright attached to the visuals.
"""
import hashlib
import os
import time
from urllib.parse import quote

import httpx

POLLINATIONS = "https://image.pollinations.ai/prompt/"


def _fallback_image(prompt: str, out_path: str, width: int, height: int) -> str:
    """A deterministic gradient placeholder (used only if generation fails)."""
    from PIL import Image  # pillow is a worker dependency

    seed = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
    c1 = ((seed >> 0) & 255, (seed >> 8) & 255, (seed >> 16) & 255)
    c2 = ((seed >> 24) & 255, (seed >> 32) & 255, (seed >> 40) & 255)
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        for x in range(width):
            px[x, y] = (r, g, b)
    img.save(out_path, "JPEG", quality=88)
    return out_path


def fetch_image(prompt: str, out_path: str, *, width: int = 1280, height: int = 720,
                seed: int | None = None, style: str = "") -> str:
    """Generate an image for `prompt` and save it to `out_path` (JPEG)."""
    full_prompt = prompt.strip()
    if style:
        full_prompt = f"{full_prompt}, {style}"
    url = (
        POLLINATIONS + quote(full_prompt)
        + f"?width={width}&height={height}&nologo=true&model=flux"
    )
    if seed is not None:
        url += f"&seed={seed}"

    last_err = None
    for attempt in range(3):
        try:
            resp = httpx.get(url, timeout=120.0, follow_redirects=True)
            if resp.status_code == 200 and resp.content and len(resp.content) > 1024:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                return out_path
            last_err = f"status {resp.status_code}, {len(resp.content)} bytes"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(3 * (attempt + 1))

    print(f"[autosource-visuals] image generation failed ({last_err}); using gradient fallback", flush=True)
    return _fallback_image(full_prompt, out_path, width, height)
