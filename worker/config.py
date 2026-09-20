"""Environment-driven configuration for the worker.

Every value comes from an environment variable so the same code runs locally
(from a .env you export) and in GitHub Actions (from repo secrets). Nothing is
hard-coded and no secret is committed.
"""
import os


def _load_dotenv() -> None:
    """Load worker/.env or ../.env into the environment for local runs.

    A no-op in GitHub Actions (no .env file there — values come from secrets).
    Existing environment variables always win over the file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(here, ".env"), os.path.join(here, "..", ".env")):
        if os.path.exists(candidate):
            for line in open(candidate, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class WorkerConfig:
    # --- Supabase (queue + tokens + transient video storage) -------------
    SUPABASE_URL = _get("SUPABASE_URL")
    # Service-role key: the worker is trusted server-side and bypasses RLS.
    SUPABASE_SERVICE_ROLE_KEY = _get("SUPABASE_SERVICE_ROLE_KEY")
    # Storage bucket the raw videos briefly live in (created automatically).
    STORAGE_BUCKET = _get("STORAGE_BUCKET", "raw-videos")

    # --- Google OAuth (YouTube upload) -----------------------------------
    GOOGLE_CLIENT_ID = _get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = _get("GOOGLE_CLIENT_SECRET")

    # --- AI (Gemini: transcription + metadata) ---------------------------
    GEMINI_API_KEY = _get("GEMINI_API_KEY")
    # Optional extra keys for rotation when one hits its quota/rate limit.
    # Provide either GEMINI_API_KEYS="k1,k2,k3" or GEMINI_API_KEY_2, _3, _4...
    GEMINI_API_KEYS = _get("GEMINI_API_KEYS")
    GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-flash-latest")

    @classmethod
    def gemini_keys(cls) -> list:
        """All configured Gemini keys, in rotation order, de-duplicated."""
        keys = []
        if cls.GEMINI_API_KEY:
            keys.append(cls.GEMINI_API_KEY)
        if cls.GEMINI_API_KEYS:
            keys += [k.strip() for k in cls.GEMINI_API_KEYS.split(",") if k.strip()]
        for i in range(2, 8):
            k = _get(f"GEMINI_API_KEY_{i}")
            if k:
                keys.append(k)
        seen, ordered = set(), []
        for k in keys:
            if k not in seen:
                seen.add(k)
                ordered.append(k)
        return ordered

    # --- YouTube upload defaults -----------------------------------------
    UPLOAD_PRIVACY_STATUS = _get("UPLOAD_PRIVACY_STATUS", "public")
    UPLOAD_CATEGORY_ID = _get("UPLOAD_CATEGORY_ID", "22")  # People & Blogs

    # --- Laptop-side push (push_local.py) --------------------------------
    # The custom folder on your device to fetch videos from.
    LOCAL_WATCH_FOLDER = _get("LOCAL_WATCH_FOLDER")
    # Optional: kick the GitHub workflow the moment a video is queued.
    GITHUB_TOKEN = _get("GITHUB_TOKEN")
    GITHUB_REPO = _get("GITHUB_REPO")  # e.g. "user/yt-automation"

    # --- Crypto ----------------------------------------------------------
    # Must match the value used by authorize.py so stored tokens decrypt.
    WORKER_SECRET_KEY = _get("WORKER_SECRET_KEY", "yt_studio_worker_default_key_change_me")

    # --- Behaviour -------------------------------------------------------
    MAX_ATTEMPTS = int(_get("MAX_ATTEMPTS", "3"))
    WORK_DIR = _get("WORK_DIR", os.path.join(os.getcwd(), ".worker-tmp"))
    VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv")

    @classmethod
    def missing_for_worker(cls) -> list:
        """Required settings for the GitHub Actions uploader."""
        required = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": cls.SUPABASE_SERVICE_ROLE_KEY,
            "GOOGLE_CLIENT_ID": cls.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": cls.GOOGLE_CLIENT_SECRET,
            # At least one Gemini key, from GEMINI_API_KEY or GEMINI_API_KEYS.
            "GEMINI_API_KEY": cls.gemini_keys()[0] if cls.gemini_keys() else "",
        }
        return [k for k, v in required.items() if not v]

    @classmethod
    def missing_for_push(cls) -> list:
        """Required settings for the laptop-side push script."""
        required = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": cls.SUPABASE_SERVICE_ROLE_KEY,
            "LOCAL_WATCH_FOLDER": cls.LOCAL_WATCH_FOLDER,
        }
        return [k for k, v in required.items() if not v]


config = WorkerConfig()
