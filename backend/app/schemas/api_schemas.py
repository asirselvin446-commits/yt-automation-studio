"""
Pydantic Validation Schemas — Request/response models for the API layer.
These decouple the API contract from the database ORM models.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Video Schemas ─────────────────────────────────────────────────────

class VideoIngestRequest(BaseModel):
    """Payload sent by the agent when a new video is detected."""
    source_path: str
    sha256_hash: str
    file_size_bytes: int
    duration_seconds: float
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    has_audio: bool = True


class VideoListResponse(BaseModel):
    """Summary response for video list endpoints."""
    id: str
    title: Optional[str] = None
    status: str
    publishing_mode: Optional[str] = None
    quality_status: Optional[str] = None
    original_filename: Optional[str] = None
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    created_at: Optional[datetime] = None
    youtube_video_id: Optional[str] = None
    selected_thumbnail: Optional[str] = None


class VideoStatusUpdate(BaseModel):
    """Request to update a video's status."""
    status: str = Field(..., description="New status: INBOX, PROCESSING, READY_FOR_APPROVAL, APPROVED, etc.")
    reason: Optional[str] = None


class TitleCandidateResponse(BaseModel):
    """A generated title candidate."""
    id: str
    text: str
    reasoning: Optional[str] = None
    style: Optional[str] = None
    estimated_ctr_impact: Optional[str] = None
    character_count: int = 0
    is_selected: bool = False


class VideoDetailResponse(BaseModel):
    """Full video detail response."""
    id: str
    title: Optional[str] = None
    status: str
    publishing_mode: Optional[str] = None
    quality_status: Optional[str] = None
    original_filename: Optional[str] = None
    source_path: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # File info
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None

    # AI-generated content
    description_short: Optional[str] = None
    description_long: Optional[str] = None
    tags: List[str] = []
    chapters: List[Dict[str, str]] = []
    title_candidates: List[TitleCandidateResponse] = []
    quality_checks: List[Dict[str, Any]] = []


# ── YouTube Schemas ───────────────────────────────────────────────────

class ChannelConnectRequest(BaseModel):
    """OAuth callback state."""
    code: str
    state: Optional[str] = None


class ChannelInfoResponse(BaseModel):
    """YouTube channel information."""
    is_connected: bool = False
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None
    channel_url: Optional[str] = None
    subscriber_count: int = 0
    video_count: int = 0
    thumbnail_url: Optional[str] = None


class UploadRequest(BaseModel):
    """Request to initiate a video upload to YouTube."""
    video_id: str
    channel_id: str
    privacy_status: str = "private"
    scheduled_publish_at: Optional[str] = None
    playlist_id: Optional[str] = None


# ── AI Schemas ────────────────────────────────────────────────────────

class AIGenerationRequest(BaseModel):
    """Request to trigger AI metadata generation."""
    video_id: str
    provider: Optional[str] = None  # gemini, openai, anthropic, local
    quality_preset: Optional[str] = "balanced"  # low_cost, balanced, high_quality


class AIProviderStatus(BaseModel):
    """Status of an AI provider."""
    name: str
    configured: bool
    model: Optional[str] = None


class AISettingsUpdate(BaseModel):
    """Update AI provider configuration."""
    default_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    local_ai_base_url: Optional[str] = None
    local_ai_model: Optional[str] = None
    quality_preset: Optional[str] = None


# ── Ideas Schemas ─────────────────────────────────────────────────────

class IdeaGenerateRequest(BaseModel):
    """Request to generate content ideas."""
    topic: str
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    estimated_length_minutes: int = 10
    count: int = 10


class ContentIdeaResponse(BaseModel):
    """A generated content idea."""
    id: str
    title: str
    hook: Optional[str] = None
    outline: Optional[str] = None
    target_audience: Optional[str] = None
    difficulty: Optional[str] = None
    status: str = "IDEA"
    created_at: Optional[datetime] = None


# ── Analytics Schemas ─────────────────────────────────────────────────

class AnalyticsRequest(BaseModel):
    """Analytics query parameters."""
    timeframe: str = "28d"
    channel_id: Optional[str] = None


class ChannelMetricsResponse(BaseModel):
    """Channel analytics metrics."""
    timeframe: str
    views: int = 0
    watch_time_hours: float = 0.0
    average_view_duration_seconds: float = 0.0
    subscribers_gained: int = 0
    subscribers_lost: int = 0
    net_subscribers: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


# ── Automation Schemas ────────────────────────────────────────────────

class AutomationSettingsResponse(BaseModel):
    """Automation toggle settings."""
    folder_monitoring: bool = True
    ai_analysis: bool = True
    approval_required: bool = True
    auto_upload: bool = False
    analytics_sync: bool = True
    auto_thumbnail: bool = False
    notification_email: bool = False


class AutomationSettingsUpdate(BaseModel):
    """Update automation settings."""
    folder_monitoring: Optional[bool] = None
    ai_analysis: Optional[bool] = None
    approval_required: Optional[bool] = None
    auto_upload: Optional[bool] = None
    analytics_sync: Optional[bool] = None
    auto_thumbnail: Optional[bool] = None
    notification_email: Optional[bool] = None


# ── System Schemas ────────────────────────────────────────────────────

class SystemHealthResponse(BaseModel):
    """System health check response."""
    status: str = "online"
    version: str
    agent_active: bool = False
    database_connected: bool = False
    youtube_connected: bool = False
    ai_provider: Optional[str] = None
    uptime_seconds: float = 0.0


class FolderStatsResponse(BaseModel):
    """Pipeline folder statistics."""
    root: str
    inbox: int = 0
    processing: int = 0
    approved: int = 0
    uploading: int = 0
    uploaded: int = 0
    failed: int = 0
    archive: int = 0
