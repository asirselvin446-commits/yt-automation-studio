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
    "You are a viral short-form YouTube storyteller for a faceless channel. You "
    "write vivid, suspenseful, TRUE micro-stories that hook in 2 seconds and pay "
    "off at the end. Cinematic and amazing, never a dry list. Never invent false "
    "facts. Everything original."
)


def _fallback_script(niche: str) -> Dict[str, Any]:
    """A safe, generic script so a run never fails just because Gemini is down."""
    topic = f"{niche} facts"
    beats = [
        {"narration": f"Here are some fascinating things about {niche} you probably didn't know.",
         "image_prompt": f"cinematic establishing shot representing {niche}, dramatic lighting",
         "visual_query": f"{niche}"},
        {"narration": "The details behind it are stranger than they first appear.",
         "image_prompt": f"detailed close-up illustrating {niche}, vivid colors",
         "visual_query": f"{niche} closeup"},
        {"narration": "Scientists are still uncovering new information about it today.",
         "image_prompt": f"a discovery or research scene about {niche}, atmospheric",
         "visual_query": "science research lab"},
        {"narration": "And it connects to everyday life in ways most people overlook.",
         "image_prompt": f"everyday scene subtly connected to {niche}, warm tones",
         "visual_query": "city people street"},
        {"narration": "If that amazed you, follow for a new story every single day.",
         "image_prompt": f"inspiring wide shot themed around {niche}, golden hour",
         "visual_query": "sunrise landscape aerial"},
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
                    beats: int = 5) -> Dict[str, Any]:
    """Return {topic, title, description, tags[], hook, beats[{narration, image_prompt, visual_query}]}."""
    avoid = ", ".join((avoid_topics or [])[:40]) or "none yet"
    prompt = f"""
Write ONE original, jaw-dropping YouTube SHORT (vertical, ~35-55 seconds) for a
faceless channel in this niche: "{niche}".

Tell it as a gripping MICRO-STORY, not a dry list: a 2-second hook that makes it
impossible to scroll past, rising curiosity, then a satisfying payoff. Make the
viewer feel amazed. Everything must be TRUE.

Pick a specific, fresh angle. Do NOT repeat any of these already-covered topics: {avoid}.

Return PURE JSON in exactly this shape:
{{
  "topic": "the specific angle you chose (a few words)",
  "title": "a scroll-stopping title under 80 characters (add #shorts at the end)",
  "description": "1-2 punchy sentences, then 5-7 relevant hashtags including #shorts",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6"],
  "hook": "the spoken opening line — a 2-second pattern-interrupt that creates instant curiosity",
  "beats": [
    {{
      "narration": "one short spoken sentence that advances the story (natural, punchy)",
      "image_prompt": "a vivid, concrete scene to illustrate it (for an AI image generator; no text in the image)",
      "visual_query": "2-4 simple English keywords to find matching stock B-ROLL video (concrete nouns/actions, e.g. 'ocean waves aerial')"
    }}
  ]
}}

Rules:
- Exactly {beats} beats; the hook is spoken FIRST and is separate from beats.
- Keep sentences SHORT so the whole thing stays under ~55 seconds when read aloud.
- Every fact true and non-controversial. No medical, legal, or financial advice.
- Narration: natural spoken English, no stage directions, no emojis, no hashtags.
- visual_query must be plain, filmable keywords a stock library would have (avoid abstract concepts).
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
                "visual_query": str(b.get("visual_query") or data.get("topic") or niche).strip(),
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
