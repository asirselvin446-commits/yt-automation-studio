"""Text-to-speech for the auto-source engine.

Providers, tried in order of preference with automatic fallback so the pipeline
never stalls on one flaky endpoint:

  * elevenlabs — the most human/natural voices (free tier ~10k chars/month).
                 Used only when a key is provided; any failure falls back.
  * fish       — Fish Audio (natural/cloned voices) while its free credits last.
  * edge       — Microsoft Edge neural voices via edge-tts. Free, no key,
                 unlimited. The $0 backbone. Newer "Multilingual" voices
                 (Ava/Andrew/Emma/Brian) sound noticeably more human.
  * gtts       — Google Translate TTS. Robotic but always works (last resort).

Every call returns the path to an mp3 written at out_path.
"""
import asyncio
import os
from typing import Optional

import httpx

# Newer conversational Microsoft voice — much more human than the old Aria.
DEFAULT_EDGE_VOICE = "en-US-AvaMultilingualNeural"
FISH_TTS_URL = "https://api.fish.audio/v1/tts"
ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
# ElevenLabs "Rachel" — a natural default when the user doesn't pick a voice.
DEFAULT_ELEVEN_VOICE = "21m00Tcm4TlvDq8ikWAM"


async def _edge_save(text: str, out_path: str, voice: str) -> None:
    import edge_tts  # imported lazily so the module loads even if absent
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def _synthesize_edge(text: str, out_path: str, voice: str) -> str:
    asyncio.run(_edge_save(text, out_path, voice or DEFAULT_EDGE_VOICE))
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        raise RuntimeError("edge-tts produced an empty file")
    return out_path


def _synthesize_gtts(text: str, out_path: str) -> str:
    """Free, keyless fallback (Google Translate TTS). Robotic but reliable."""
    from gtts import gTTS
    gTTS(text=text, lang="en").save(out_path)
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
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
    if not (os.path.getsize(out_path) > 0):
        raise RuntimeError("Fish Audio returned an empty file")
    return out_path


def _synthesize_eleven(text: str, out_path: str, api_key: str,
                       voice_id: Optional[str]) -> str:
    """Best-effort ElevenLabs TTS (very human). Raises on failure to fall back."""
    url = ELEVEN_TTS_URL.format(voice_id=voice_id or DEFAULT_ELEVEN_VOICE)
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    with httpx.stream(
        "POST", url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
        json=body, timeout=120.0,
    ) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.read()[:200]}")
        with open(out_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                f.write(chunk)
    if not (os.path.getsize(out_path) > 0):
        raise RuntimeError("ElevenLabs returned an empty file")
    return out_path


def synthesize(text: str, out_path: str, *, provider: str = "edge",
               voice: str = "", fish_api_key: str = "", fish_voice: str = "",
               eleven_api_key: str = "", eleven_voice: str = "") -> str:
    """Narrate `text` to `out_path` (mp3). Always falls back to free edge/gTTS."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Cannot synthesize empty text")

    # Preferred premium provider first; fall through on any failure so a single
    # flaky endpoint or exhausted free tier never fails the whole video.
    if provider == "elevenlabs" and eleven_api_key:
        try:
            return _synthesize_eleven(text, out_path, eleven_api_key, eleven_voice or None)
        except Exception as e:  # noqa: BLE001
            print(f"[autosource-voice] ElevenLabs failed ({e}); falling back to edge-tts", flush=True)
    elif provider == "fish" and fish_api_key:
        try:
            return _synthesize_fish(text, out_path, fish_api_key, fish_voice or None)
        except Exception as e:  # noqa: BLE001
            print(f"[autosource-voice] Fish Audio failed ({e}); falling back to edge-tts", flush=True)

    try:
        return _synthesize_edge(text, out_path, voice)
    except Exception as e:  # noqa: BLE001 — edge's endpoint 403s when tokens rotate
        print(f"[autosource-voice] edge-tts failed ({e}); falling back to gTTS", flush=True)

    return _synthesize_gtts(text, out_path)
