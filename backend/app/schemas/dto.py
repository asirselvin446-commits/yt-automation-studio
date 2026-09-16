from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# System & Status
# ------------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    database_connected: bool
    agent_active: bool
    watch_folder: str
    timestamp: datetime


class SystemFolderStats(BaseModel):
    root: str
    inbox_count: int
    processing_count: int
    approved_count: int
    uploading_count: int
    uploaded_count: int
    failed_count: int
    archive_count: int


# ------------------------------------------------------------------------------
# Video & Media
# ------------------------------------------------------------------------------
class VideoFileDTO(BaseModel):
    sha256_hash: str
    file_size_bytes: int
    duration_seconds: float
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    has_audio: bool = True
    container_format: Optional[str] = None
    is_corrupted: bool = False


class TitleCandidateDTO(BaseModel):
    id: Optional[str] = None
    candidate_index: int
    title_text: str
    reasoning: Optional[str] = None
    estimated_intent: Optional[str] = None
    character_length: int
    is_selected: bool = False


class DescriptionDTO(BaseModel):
    short_description: Optional[str] = None
    long_description: str
    call_to_action: Optional[str] = None
    links_placeholder: Optional[str] = None
    hashtags: List[str] = []
    chapters: List[Dict[str, Any]] = []


class TagsDTO(BaseModel):
    primary_keywords: List[str] = []
    secondary_keywords: List[str] = []
    long_tail_keywords: List[str] = []
    combined_tags_string: Optional[str] = None
    tag_count: int = 0


class ThumbnailDTO(BaseModel):
    id: Optional[str] = None
    concept_title: Optional[str] = None
    text_suggestions: Optional[str] = None
    visual_composition: Optional[str] = None
    preview_url: Optional[str] = None
    local_file_path: Optional[str] = None
    is_selected: bool = False
    status: str = "DRAFT"


class QualityCheckItem(BaseModel):
    name: str
    passed: bool
    status: str  # VALID, WARNING, BLOCKED, ERROR
    message: str


class QualityCheckResult(BaseModel):
    overall_status: str  # READY, WARNING, BLOCKED, ERROR
    can_upload: bool
    checks: List[QualityCheckItem]


class VideoDetailDTO(BaseModel):
    id: str
    title: str
    status: str
    publishing_mode: str
    quality_status: str
    original_filename: str
    source_path: str
    current_folder_path: str
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    privacy_status: str
    created_at: datetime
    updated_at: datetime
    file_info: Optional[VideoFileDTO] = None
    titles: List[TitleCandidateDTO] = []
    description: Optional[DescriptionDTO] = None
    tags: Optional[TagsDTO] = None
    thumbnails: List[ThumbnailDTO] = []
    quality_check: Optional[QualityCheckResult] = None
    transcript_summary: Optional[str] = None


class VideoListDTO(BaseModel):
    id: str
    title: str
    status: str
    publishing_mode: str
    quality_status: str
    original_filename: str
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime
    youtube_video_id: Optional[str] = None
    selected_thumbnail: Optional[str] = None


# ------------------------------------------------------------------------------
# Channel & YouTube
# ------------------------------------------------------------------------------
class ChannelDTO(BaseModel):
    id: str
    youtube_channel_id: str
    title: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int
    video_count: int
    view_count: int
    is_connected: bool


# ------------------------------------------------------------------------------
# Content Ideas & Calendar
# ------------------------------------------------------------------------------
class ContentIdeaCreateDTO(BaseModel):
    topic: str
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    video_type: Optional[str] = None
    estimated_length_minutes: int = 10


class ContentIdeaDTO(BaseModel):
    id: str
    topic: str
    title_concept: str
    hook: Optional[str] = None
    video_structure: Optional[str] = None
    target_audience: Optional[str] = None
    production_difficulty: str
    estimated_length_minutes: int
    status: str
    created_at: datetime


class CalendarItemDTO(BaseModel):
    id: str
    title: str
    scheduled_datetime: datetime
    status: str
    color_code: str
    video_id: Optional[str] = None
    notes: Optional[str] = None


# ------------------------------------------------------------------------------
# Automation & Settings
# ------------------------------------------------------------------------------
class AutomationSettingsDTO(BaseModel):
    folder_monitoring: bool = True
    ai_analysis: bool = True
    metadata_generation: bool = True
    thumbnail_generation: bool = True
    approval_required: bool = True  # Default true for safety
    auto_upload: bool = False
    auto_scheduling: bool = False
    analytics_sync: bool = True
    ai_insights: bool = True
    watch_folder_root: str = "D:\\YT-Automation"
    default_ai_provider: str = "gemini"
    ai_cost_preset: str = "balanced"


class AISettingsUpdateDTO(BaseModel):
    default_provider: str
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    local_ai_url: Optional[str] = None
    ai_cost_preset: Optional[str] = "balanced"


# ------------------------------------------------------------------------------
# Brain & Q&A
# ------------------------------------------------------------------------------
class BrainQueryRequest(BaseModel):
    question: str


class BrainQueryResponse(BaseModel):
    data_basis: Dict[str, Any]
    interpretation: str
    actionable_suggestions: List[str]
    confidence_rating: str
