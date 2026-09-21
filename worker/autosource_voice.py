"""Text-to-speech for the auto-source engine.

Two providers, with automatic fallback so the pipeline never stalls:

  * edge  — Microsoft Edge neural voices via edge-tts. Free, no key, unlimited.
            This is the $0 backbone that keeps the channel running forever.
  * fish  — Fish Audio (nicer/cloned voices) while its free credits last.
            Used only when a key is provided; any failure falls back to edge.

Every call returns the path to an mp3 written at out_path.
"""
import asyncio
from typing import Optional

import httpx

# A pleasant default narration voice; overridable from the app config.
DEFAULT_EDGE_VOICE = "en-US-AriaNeural"
FISH_TTS_URL = "https://api.fish.audio/v1/tts"


async def _edge_save(text: str, out_path: str, voice: str) -> None:
    import edge_tts  # imported lazily so the module loads even if absent
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def _synthesize_edge(text: str, out_path: str, voice: str) -> str:
    asyncio.run(_edge_save(text, out_path, voice or DEFAULT_EDGE_VOICE))
    import os as _os
    if not (_os.path.exists(out_path) and _os.path.getsize(out_path) > 0):
        raise RuntimeError("edge-tts produced an empty file")
    return out_path


def _synthesize_gtts(text: str, out_path: str) -> str:
    """Free, keyless fallback (Google Translate TTS). Robotic but reliable."""
    from gtts import gTTS
    gTTS(text=text, lang="en").save(out_path)
    import os as _os
    if not (_os.path.exists(out_path) and _os.path.getsize(out_path) > 0):
        raise RuntimeError("gTTS produced an empty file")
    return out_path


def _synthesize_fish(text: str, out_path: str, api_key: str,
                     reference_id: Optional[str]) -> str:
    """Best-effort Fish Audio TTS. Raises on any problem so the caller falls back."""
    body = {"text": text, "format": "mp3"}
    if reference_id:
        body["reference_id"] = reference_id
    with httpx.stream(
        "POST", FISH_TTS_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body, timeout=120.0,
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Fish Audio error {resp.status_code}: {resp.read()[:200]}")
        with open(out_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                f.write(chunk)
    if not (__import__("os").path.getsize(out_path) > 0):
        raise RuntimeError("Fish Audio returned an empty file")
    return out_path


def synthesize(text: str, out_path: str, *, provider: str = "edge",
               voice: str = "", fish_api_key: str = "",
               fish_voice: str = "") -> str:
    """Narrate `text` to `out_path` (mp3). Falls back to free edge-tts on failure."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Cannot synthesize empty text")

    # Try providers in order of preference; fall through on any failure so a
    # single flaky endpoint never fails the whole video.
    if provider == "fish" and fish_api_key:
        try:
            return _synthesize_fish(text, out_path, fish_api_key, fish_voice or None)
        except Exception as e:  # noqa: BLE001 — free tier exhausted / network / etc.
            print(f"[autosource-voice] Fish Audio failed ({e}); falling back to edge-tts", flush=True)

    try:
        return _synthesize_edge(text, out_path, voice)
    except Exception as e:  # noqa: BLE001 — edge's endpoint 403s when tokens rotate
        print(f"[autosource-voice] edge-tts failed ({e}); falling back to gTTS", flush=True)

    return _synthesize_gtts(text, out_path)
