from typing import Optional
from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import system_logger

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Retrieve or initialize Supabase Python client using configured credentials."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if settings.SUPABASE_URL:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if key:
            try:
                _supabase_client = create_client(settings.SUPABASE_URL, key)
                system_logger.info("Connected to Supabase project: %s", settings.SUPABASE_URL)
            except Exception as e:
                system_logger.error("Failed to initialize Supabase client: %s", e)
                _supabase_client = None

    return _supabase_client
