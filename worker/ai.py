"""Generate YouTube metadata from a transcript using Gemini (text, JSON mode).

One analysis pass, then title/description/tags derived from it. Prompts mirror
the desktop app's GeminiProvider so the cloud output matches what you'd get in
the UI. Never invents facts — everything is grounded in the transcript.
"""
import json
import time
from typing import Any, Dict

import httpx

from config import config
from transcribe import upload_to_gemini

GENAI = "https://generativelanguage.googleapis.com"
SYSTEM = "You are an elite YouTube content strategist. Never invent false facts not present in the transcript."


def _model_chain() -> list:
    """Preferred model first, then fallbacks for when it's overloaded (503)."""
    chain = [config.GEMINI_MODEL]
    for m in ("gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash-lite"):
        if m not in chain:
            chain.append(m)
    return chain


def gemini_post(payload: Dict[str, Any], api_key: str = None, retries_per_model: int = 2) -> httpx.Response:
    """POST generateContent for one key, retrying transient 429/503 and falling
    back across models. A persistent 429 means this key is quota-limited — the
    caller rotates to the next key."""
    key = api_key or config.GEMINI_API_KEY
    last = None
    for model in _model_chain():
        url = f"{GENAI}/v1beta/models/{model}:generateContent?key={key}"
        delay = 4.0
        for attempt in range(retries_per_model):
            last = httpx.post(url, json=payload, timeout=300.0)
            if last.status_code not in (429, 503):
                return last  # success or a non-transient error — stop here
            # 429 (quota) rarely clears fast — don't waste long retries on it.
            if last.status_code == 429:
                break
            if attempt < retries_per_model - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
        # overloaded or quota-limited on this model — try the next model
    return last


def _call_json(prompt: str) -> Dict[str, Any]:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "generationConfig": {"responseMimeType": "application/json"},
    }
    resp = None
    for key in (config.gemini_keys() or [config.GEMINI_API_KEY]):
        resp = gemini_post(payload, api_key=key)
        if resp.status_code != 429:
            break  # success or non-quota error — stop rotating
    if resp is None or resp.status_code != 200:
        raise RuntimeError(f"Gemini error ({getattr(resp,'status_code','?')}): {getattr(resp,'text','')}")
    raw = (
        resp.json()
        .get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    try:
        return json.loads(raw)
    except Exception:
        return {}


def generate_from_video(file_path: str, mime_type: str, display_name: str,
                        fallback_title: str = "New Video") -> Dict[str, Any]:
    """Watch the video with Gemini and return YouTube metadata.

    Works even when the video has no speech (gameplay, music, b-roll) because it
    reasons over the visuals as well as any audio. Returns
    {title, description, tags[], summary}.
    """
    prompt = """
Watch this video and produce YouTube publishing metadata based on what actually
happens in it (both the visuals and any speech or music). Respond with PURE JSON:
{
  "title": "One compelling, accurate title under 100 characters.",
  "description": "A 2-4 paragraph YouTube description grounded in the video, ending with 3-5 relevant hashtags.",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "summary": "2-3 sentence factual summary of the video."
}
Do not invent facts that aren't supported by the video.
"""
    # Try each Gemini key in turn; a file is scoped to the key that uploaded it,
    # so a key rotation re-uploads with the new key.
    keys = config.gemini_keys() or [config.GEMINI_API_KEY]
    resp = None
    for i, key in enumerate(keys):
        file_uri = upload_to_gemini(file_path, mime_type or "video/mp4", display_name, api_key=key)
        resp = gemini_post({
            "contents": [{"parts": [
                {"file_data": {"mime_type": mime_type or "video/mp4", "file_uri": file_uri}},
                {"text": prompt},
            ]}],
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }, api_key=key)
        if resp.status_code != 429:
            break  # success or a non-quota error — no point rotating keys
        if i < len(keys) - 1:
            print(f"[ai] Gemini key #{i + 1} quota-limited; rotating to next key", flush=True)
    if resp is None or resp.status_code != 200:
        raise RuntimeError(f"Gemini video analysis error ({getattr(resp,'status_code','?')}): {getattr(resp,'text','')}")
    raw = (
        resp.json().get("candidates", [{}])[0]
        .get("content", {}).get("parts", [{}])[0].get("text", "{}")
    )
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    title = (data.get("title") or fallback_title)[:100]
    tags = [t for t in (data.get("tags") or []) if isinstance(t, str)][:50]
    return {
        "title": title,
        "description": data.get("description") or "Uploaded automatically by YT Automation Studio.",
        "tags": tags,
        "summary": data.get("summary", ""),
    }


def generate_metadata(transcript: str, fallback_title: str = "New Video") -> Dict[str, Any]:
    """Return {title, description, tags[], summary, topics[], keywords[]}."""
    text = (transcript or "").strip()
    if not text:
        # No speech detected — return safe defaults so upload can still proceed.
        return {
            "title": fallback_title[:100],
            "description": "Uploaded automatically by YT Automation Studio.",
            "tags": [],
            "summary": "",
            "topics": [],
            "keywords": [],
        }

    prompt = f"""
Analyze this video transcript and produce YouTube publishing metadata.
Respond with PURE JSON in exactly this structure:
{{
  "summary": "2-3 sentence overview.",
  "topics": ["topic1", "topic2", "topic3"],
  "keywords": ["kw1", "kw2", "kw3", "kw4"],
  "title": "One compelling, accurate title under 100 characters.",
  "description": "A 3-4 paragraph YouTube description grounded in the transcript, ending with 3-5 relevant hashtags.",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Transcript:
{text[:12000]}
"""
    data = _call_json(prompt)
    title = (data.get("title") or fallback_title)[:100]
    tags = [t for t in (data.get("tags") or []) if isinstance(t, str)][:50]
    return {
        "title": title,
        "description": data.get("description") or "Uploaded automatically by YT Automation Studio.",
        "tags": tags,
        "summary": data.get("summary", ""),
        "topics": data.get("topics", []),
        "keywords": data.get("keywords", []),
    }
