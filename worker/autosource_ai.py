"""Write an original short video script with Gemini (free tier, key rotation).

Given a niche and a list of already-covered topics, returns a fresh, factual
"Did You Know"-style script broken into narration beats, each with an image
prompt, plus ready-to-publish YouTube metadata. Everything here is original text
the model writes — no third-party content — which is what keeps the finished
video monetization-safe.
"""
import json
from typing import Any, Dict, List

from ai import gemini_post

SYSTEM = (
    "You are a professional short-form YouTube scriptwriter for a faceless "
    "facts/explainer channel. Write accurate, engaging narration. Never invent "
    "false facts. Keep it original."
)


def _fallback_script(niche: str) -> Dict[str, Any]:
    """A safe, generic script so a run never fails just because Gemini is down."""
    topic = f"{niche} facts"
    beats = [
        {"narration": f"Here are some fascinating things about {niche} you probably didn't know.",
         "image_prompt": f"cinematic establishing shot representing {niche}, dramatic lighting"},
        {"narration": "Number one: the details behind it are stranger than they first appear.",
         "image_prompt": f"detailed close-up illustrating {niche}, vivid colors"},
        {"narration": "Number two: scientists and historians are still uncovering new information.",
         "image_prompt": f"a discovery or research scene about {niche}, atmospheric"},
        {"narration": "Number three: it connects to everyday life in ways most people overlook.",
         "image_prompt": f"everyday scene subtly connected to {niche}, warm tones"},
        {"narration": "If you found that interesting, subscribe for a new fact every single day.",
         "image_prompt": f"inspiring wide shot themed around {niche}, golden hour"},
    ]
    return {
        "topic": topic,
        "title": f"{niche.title()} Facts You Won't Believe",
        "description": (
            f"Fascinating {niche} facts explained in under a minute.\n\n"
            "New videos daily. Subscribe for more!\n\n#facts #didyouknow #shorts"
        ),
        "tags": [niche, f"{niche} facts", "did you know", "facts", "educational"],
        "hook": f"Did you know these {niche} facts?",
        "beats": beats,
    }


def generate_script(niche: str, avoid_topics: List[str] | None = None,
                    beats: int = 6) -> Dict[str, Any]:
    """Return {topic, title, description, tags[], hook, beats[{narration, image_prompt}]}."""
    avoid = ", ".join((avoid_topics or [])[:40]) or "none yet"
    prompt = f"""
Create ONE original short YouTube video (about 45-75 seconds) for a faceless
channel in this niche: "{niche}".

Pick a specific, fresh topic within the niche. Do NOT repeat any of these
already-covered topics: {avoid}.

Return PURE JSON in exactly this shape:
{{
  "topic": "the specific topic you chose (a few words)",
  "title": "a punchy YouTube title under 90 characters",
  "description": "2-3 sentence description grounded in the script, then 4-6 relevant hashtags",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6"],
  "hook": "a 1-sentence opening hook that creates curiosity in the first 3 seconds",
  "beats": [
    {{
      "narration": "one spoken sentence (natural, punchy, factual)",
      "image_prompt": "a vivid, concrete visual description to illustrate this sentence (for an AI image generator; no text/words in the image)"
    }}
  ]
}}

Rules:
- Exactly {beats} beats, plus the hook is spoken first (do not include the hook inside beats).
- Every fact must be true and non-controversial. No medical, legal, or financial advice.
- Narration should sound natural when read aloud. No stage directions, no emojis in narration.
- image_prompt must describe a real, filmable-looking scene — never ask for on-screen text.
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "generationConfig": {"responseMimeType": "application/json"},
    }

    # Rotate across all configured Gemini keys; fall back on any failure.
    from config import config
    resp = None
    for key in (config.gemini_keys() or [config.GEMINI_API_KEY]):
        try:
            resp = gemini_post(payload, api_key=key)
        except Exception:
            resp = None
            continue
        if resp is not None and resp.status_code != 429:
            break

    if resp is None or resp.status_code != 200:
        print(f"[autosource-ai] Gemini unavailable ({getattr(resp,'status_code','?')}); using fallback script", flush=True)
        return _fallback_script(niche)

    try:
        raw = (resp.json().get("candidates", [{}])[0]
               .get("content", {}).get("parts", [{}])[0].get("text", "{}"))
        data = json.loads(raw)
    except Exception:
        return _fallback_script(niche)

    # Validate / coerce.
    beats_out = []
    for b in (data.get("beats") or []):
        if isinstance(b, dict) and b.get("narration"):
            beats_out.append({
                "narration": str(b.get("narration")).strip(),
                "image_prompt": str(b.get("image_prompt") or data.get("topic") or niche).strip(),
            })
    if not beats_out:
        return _fallback_script(niche)

    hook = str(data.get("hook") or "").strip()
    tags = [str(t) for t in (data.get("tags") or []) if isinstance(t, str)][:20] or [niche, "facts"]
    return {
        "topic": str(data.get("topic") or niche).strip(),
        "title": (str(data.get("title") or f"{niche.title()} Facts").strip())[:95],
        "description": str(data.get("description") or "").strip()
                       or f"Fascinating {niche} facts.\n\n#facts #didyouknow",
        "tags": tags,
        "hook": hook,
        "beats": beats_out,
    }
