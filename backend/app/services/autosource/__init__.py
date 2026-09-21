"""Desktop-side control panel for the cloud Auto-Source engine.

The heavy lifting (script, voice, images, ffmpeg, upload) runs in GitHub Actions
so it works 24/7 with the laptop off. This module is the thin control surface the
desktop app uses to:

  * read/write the single config row in Supabase (niche, frequency, voice, …),
  * read recent run status for the live view,
  * fire a repository_dispatch so "Generate one now" starts within a minute.

Nothing here generates video — it only configures and monitors the cloud engine.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from supabase import create_client, Client

from app.core.config import settings
from app.core.logging import system_logger

_DEFAULT_CONFIG: Dict[str, Any] = {
    "id": "default",
    "enabled": False,
    "niche": "amazing facts",
    "per_day": 1,
    "provider": "edge",
    "voice": "en-US-AriaNeural",
    "fish_api_key": "",
    "fish_voice": "",
}

_ALLOWED_PROVIDERS = ("edge", "fish")


def _client() -> Optional[Client]:
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_config() -> Dict[str, Any]:
    """Current engine config, merged over safe defaults."""
    db = _client()
    if db is None:
        return {**_DEFAULT_CONFIG, "configured": False}
    try:
        res = db.table("autosource_config").select("*").eq("id", "default").limit(1).execute()
        rows = res.data or []
        cfg = {**_DEFAULT_CONFIG, **(rows[0] if rows else {})}
    except Exception as e:  # table may not exist yet
        system_logger.warning(f"autosource get_config failed: {e}")
        cfg = {**_DEFAULT_CONFIG}
    # Never expose the Fish key back to the UI — just whether one is set.
    cfg["fish_api_key_set"] = bool(cfg.get("fish_api_key"))
    cfg.pop("fish_api_key", None)
    cfg["configured"] = True
    return cfg


def set_config(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and upsert the config row. Returns the sanitized config."""
    db = _client()
    if db is None:
        raise RuntimeError("Supabase is not configured — add your keys first.")

    row: Dict[str, Any] = {"id": "default", "updated_at": _now()}
    if "enabled" in fields:
        row["enabled"] = bool(fields["enabled"])
    if "niche" in fields and str(fields["niche"]).strip():
        row["niche"] = str(fields["niche"]).strip()[:120]
    if "per_day" in fields:
        row["per_day"] = max(1, min(8, int(fields["per_day"])))
    if "provider" in fields:
        p = str(fields["provider"]).strip().lower()
        row["provider"] = p if p in _ALLOWED_PROVIDERS else "edge"
    if "voice" in fields:
        row["voice"] = str(fields["voice"]).strip()[:80]
    if "fish_voice" in fields:
        row["fish_voice"] = str(fields["fish_voice"]).strip()[:120]
    # Only overwrite the key when a non-empty value is supplied (blank keeps it).
    if fields.get("fish_api_key"):
        row["fish_api_key"] = str(fields["fish_api_key"]).strip()

    db.table("autosource_config").upsert(row).execute()
    return get_config()


def list_runs(limit: int = 20) -> List[Dict[str, Any]]:
    db = _client()
    if db is None:
        return []
    try:
        res = (
            db.table("autosource_runs")
            .select("id,status,stage,niche,topic,title,youtube_url,publish_at,error,created_at,updated_at")
            .order("created_at", desc=True).limit(limit).execute()
        )
        return res.data or []
    except Exception as e:
        system_logger.warning(f"autosource list_runs failed: {e}")
        return []


def get_status() -> Dict[str, Any]:
    """Everything the Auto-Source page needs in one call."""
    runs = list_runs()
    active = next((r for r in runs if (r.get("status") or "").upper() == "RUNNING"), None)
    return {
        "config": get_config(),
        "runs": runs,
        "active": active,
        "github_ready": bool(settings.GITHUB_TOKEN and settings.GITHUB_REPO),
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
    }


def generate_now() -> Dict[str, Any]:
    """Fire a repository_dispatch so the cloud makes one video immediately."""
    token = settings.GITHUB_TOKEN or ""
    repo = settings.GITHUB_REPO or ""
    if not (token and repo):
        return {"started": False,
                "reason": "GitHub isn't connected yet (set GITHUB_TOKEN and GITHUB_REPO)."}
    cfg = get_config()
    if not cfg.get("enabled"):
        return {"started": False,
                "reason": "Turn the engine on first, then generate."}
    try:
        resp = httpx.post(
            f"https://api.github.com/repos/{repo}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"event_type": "autosource-now"},
            timeout=20.0,
        )
        if resp.status_code not in (200, 201, 204):
            return {"started": False, "reason": f"GitHub responded {resp.status_code}: {resp.text[:200]}"}
        system_logger.info("Auto-source: dispatched a cloud generation run.")
        return {"started": True, "reason": "Generating in the cloud — it'll appear below shortly."}
    except Exception as e:  # noqa: BLE001
        return {"started": False, "reason": f"Could not reach GitHub: {e}"}


def start() -> None:
    """No-op: generation runs in the cloud. Kept for API symmetry."""
    return None
