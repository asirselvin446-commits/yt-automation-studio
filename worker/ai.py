"""Generate YouTube metadata from a transcript using Gemini (text, JSON mode).

One analysis pass, then title/description/tags derived from it. Prompts mirror
the desktop app's GeminiProvider so the cloud output matches what you'd get in
the UI. Never invents facts — everything is grounded in the transcript.
"""
import json
from typing import Any, Dict

import httpx

from config import config

GENAI = "https://generativelanguage.googleapis.com"
SYSTEM = "You are an elite YouTube content strategist. Never invent false facts not present in the transcript."


def _call_json(prompt: str) -> Dict[str, Any]:
    key = config.GEMINI_API_KEY
    resp = httpx.post(
        f"{GENAI}/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=90.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini error ({resp.status_code}): {resp.text}")
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
