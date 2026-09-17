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


store = Store()
