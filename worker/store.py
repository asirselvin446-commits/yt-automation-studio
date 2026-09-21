"""Supabase data access for the worker (job queue, dedup ledger, credentials).

Uses the supabase-py REST client with the service-role key, so all reads/writes
bypass RLS. Supabase is the only persistent state, which is what lets the laptop
and GitHub Actions hand work off to each other without talking directly.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from supabase import create_client, Client

from config import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self):
        self.db: Client = create_client(
            config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY
        )

    # --- credentials -----------------------------------------------------
    # Google forbids Drive + YouTube scopes in one consent, so we store two
    # separate grants: id "google" (YouTube) and id "drive" (Drive).
    def get_google_credentials(self, cred_id: str = "google") -> Optional[Dict[str, Any]]:
        res = (
            self.db.table("worker_credentials")
            .select("*").eq("id", cred_id).limit(1).execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def save_google_credentials(
        self, refresh_token_encrypted: str, scopes: List[str],
        channel_id: Optional[str], channel_title: Optional[str],
        cred_id: str = "google",
    ) -> None:
        self.db.table("worker_credentials").upsert({
            "id": cred_id,
            "refresh_token_encrypted": refresh_token_encrypted,
            "scopes": scopes,
            "youtube_channel_id": channel_id,
            "youtube_channel_title": channel_title,
            "updated_at": _now(),
        }).execute()

    # --- ingest ledger / queue ------------------------------------------
    def get_item_by_sha(self, sha256: str) -> Optional[Dict[str, Any]]:
        res = (
            self.db.table("ingest_items")
            .select("*").eq("sha256", sha256).limit(1).execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def enqueue(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a newly-seen video as QUEUED. Caller sets sha256/paths."""
        row = {**row, "status": "QUEUED", "created_at": _now(), "updated_at": _now()}
        res = self.db.table("ingest_items").insert(row).execute()
        return (res.data or [row])[0]

    def next_queued(self) -> Optional[Dict[str, Any]]:
        res = (
            self.db.table("ingest_items")
            .select("*").eq("status", "QUEUED")
            .order("created_at", desc=False).limit(1).execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def uploaded_pending_local_cleanup(self) -> List[Dict[str, Any]]:
        """UPLOADED items whose local file hasn't been deleted yet."""
        res = (
            self.db.table("ingest_items")
            .select("*").eq("status", "UPLOADED").eq("local_deleted", False)
            .execute()
        )
        return res.data or []

    def update_item(self, item_id: str, **fields) -> None:
        fields["updated_at"] = _now()
        self.db.table("ingest_items").update(fields).eq("id", item_id).execute()

    # --- auto-source engine (cloud content generation) -------------------
    def get_autosource_config(self) -> Dict[str, Any]:
        """The single config row the desktop app writes and the worker reads."""
        try:
            res = (
                self.db.table("autosource_config")
                .select("*").eq("id", "default").limit(1).execute()
            )
            rows = res.data or []
            return rows[0] if rows else {}
        except Exception:
            return {}

    def recent_autosource_topics(self, limit: int = 40) -> List[str]:
        """Topics already produced, so the model doesn't repeat itself."""
        try:
            res = (
                self.db.table("autosource_runs")
                .select("topic").order("created_at", desc=True).limit(limit).execute()
            )
            return [r["topic"] for r in (res.data or []) if r.get("topic")]
        except Exception:
            return []

    def count_autosource_done_since(self, iso_ts: str) -> int:
        """How many videos finished since iso_ts (used for per-day limiting)."""
        try:
            res = (
                self.db.table("autosource_runs")
                .select("id", count="exact")
                .gte("created_at", iso_ts)
                .in_("status", ["DONE", "UPLOADED"])
                .execute()
            )
            return res.count or 0
        except Exception:
            return 0

    def start_autosource_run(self, niche: str) -> str:
        """Create a RUNNING run row and return its id (for live status)."""
        row = {
            "status": "RUNNING", "stage": "starting", "niche": niche,
            "created_at": _now(), "updated_at": _now(),
        }
        res = self.db.table("autosource_runs").insert(row).execute()
        return (res.data or [{}])[0].get("id")

    def update_autosource_run(self, run_id: str, **fields) -> None:
        if not run_id:
            return
        fields["updated_at"] = _now()
        try:
            self.db.table("autosource_runs").update(fields).eq("id", run_id).execute()
        except Exception as e:  # noqa: BLE001 — never let status logging crash a run
            print(f"[store] autosource run update failed: {e}", flush=True)


store = Store()
