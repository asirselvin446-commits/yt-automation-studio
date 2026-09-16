from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Basics
    APP_NAME: str = "YT Automation Studio"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_SECRET_KEY: str = "yt_studio_dev_secret_key_38f8a91c7b"

    # Server Configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://127.0.0.1:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Database: Supabase PostgreSQL (or fallback to local SQLite)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./yt_automation.db"

    # Google / YouTube OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/youtube/oauth2callback"
    YOUTUBE_API_KEY: Optional[str] = None

    # AI Provider Settings
    DEFAULT_AI_PROVIDER: str = "gemini"  # gemini | openai | anthropic | local
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    LOCAL_AI_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_AI_MODEL: str = "llama3:8b"
    DEFAULT_AI_QUALITY_PRESET: str = "balanced"  # low_cost | balanced | high_quality

    # Local Storage & Windows Folder Structure
    YT_AUTOMATION_ROOT: str = "./data/YT-Automation"
    AGENT_AUTH_TOKEN: str = "agent_secret_token_default_local"
    AGENT_POLL_INTERVAL_SECONDS: int = 2
    STABLE_FILE_TIMEOUT_SECONDS: int = 5
    MAX_UPLOAD_RETRY_COUNT: int = 5

    @property
    def root_path(self) -> Path:
        return Path(self.YT_AUTOMATION_ROOT).resolve()

    @property
    def inbox_path(self) -> Path:
        return self.root_path / "INBOX"

    @property
    def processing_path(self) -> Path:
        return self.root_path / "PROCESSING"

    @property
    def approved_path(self) -> Path:
        return self.root_path / "APPROVED"

    @property
    def uploading_path(self) -> Path:
        return self.root_path / "UPLOADING"

    @property
    def uploaded_path(self) -> Path:
        return self.root_path / "UPLOADED"

    @property
    def failed_path(self) -> Path:
        return self.root_path / "FAILED"

    @property
    def archive_path(self) -> Path:
        return self.root_path / "ARCHIVE"

    @property
    def thumbnails_path(self) -> Path:
        return self.root_path / "THUMBNAILS"

    @property
    def temp_path(self) -> Path:
        return self.root_path / "TEMP"

    def ensure_directories(self) -> None:
        """Create all required pipeline folders if they do not exist."""
        folders = [
            self.root_path,
            self.inbox_path,
            self.processing_path,
            self.approved_path,
            self.uploading_path,
            self.uploaded_path,
            self.failed_path,
            self.archive_path,
            self.thumbnails_path,
            self.temp_path,
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)


settings = Settings()
