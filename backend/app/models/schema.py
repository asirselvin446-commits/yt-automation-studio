import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, BigInteger,
    Numeric, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    role = Column(String(50), default="creator")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    channels = relationship("Channel", back_populates="profile", cascade="all, delete-orphan")
    automation_settings = relationship("AutomationSettings", back_populates="profile", uselist=False)
    notifications = relationship("Notification", back_populates="profile", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    youtube_channel_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    custom_url = Column(String(100), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    subscriber_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    view_count = Column(BigInteger, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    profile = relationship("Profile", back_populates="channels")
    connection = relationship("YouTubeConnection", back_populates="channel", uselist=False, cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="channel")


class YouTubeConnection(Base):
    __tablename__ = "youtube_connections"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    token_uri = Column(String(255), default="https://oauth2.googleapis.com/token")
    client_id = Column(String(255), nullable=True)
    scopes = Column(JSON, default=list)
    expires_at = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, default=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    channel = relationship("Channel", back_populates="connection")


class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    # INBOX, PROCESSING, READY_FOR_APPROVAL, APPROVED, UPLOADING, UPLOADED, FAILED, CANCELLED
    status = Column(String(50), default="INBOX", nullable=False)
    # APPROVAL_REQUIRED, AUTO_PUBLISH
    publishing_mode = Column(String(50), default="APPROVAL_REQUIRED", nullable=False)
    # PENDING, READY, WARNING, BLOCKED, ERROR
    quality_status = Column(String(50), default="PENDING", nullable=False)
    source_path = Column(Text, nullable=False)
    current_folder_path = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=False)
    active_metadata_version = Column(Integer, default=1)
    scheduled_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    youtube_video_id = Column(String(100), nullable=True)
    youtube_url = Column(Text, nullable=True)
    privacy_status = Column(String(50), default="private")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    channel = relationship("Channel", back_populates="videos")
    file_info = relationship("VideoFile", back_populates="video", uselist=False, cascade="all, delete-orphan")
    analysis = relationship("VideoAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    metadata_generations = relationship("MetadataGeneration", back_populates="video", cascade="all, delete-orphan")
    thumbnails = relationship("ThumbnailRecord", back_populates="video", cascade="all, delete-orphan")
    upload_jobs = relationship("UploadJob", back_populates="video", cascade="all, delete-orphan")


class VideoFile(Base):
    __tablename__ = "video_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    sha256_hash = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    duration_seconds = Column(Numeric(10, 3), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    aspect_ratio = Column(String(20), nullable=True)
    fps = Column(Numeric(6, 2), nullable=True)
    video_codec = Column(String(50), nullable=True)
    video_bitrate = Column(BigInteger, nullable=True)
    has_audio = Column(Boolean, default=True)
    audio_codec = Column(String(50), nullable=True)
    audio_channels = Column(Integer, nullable=True)
    audio_sample_rate = Column(Integer, nullable=True)
    container_format = Column(String(50), nullable=True)
    is_corrupted = Column(Boolean, default=False)
    inspection_raw = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="file_info")


class VideoAnalysis(Base):
    __tablename__ = "video_analysis"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    audio_extracted_path = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    topics = Column(JSON, default=list)
    keywords = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    target_audience = Column(Text, nullable=True)
    content_category = Column(String(100), nullable=True)
    important_moments = Column(JSON, default=list)
    raw_ai_payload = Column(JSON, nullable=True)
    ai_provider = Column(String(50), nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_consumed = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="analysis")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    confidence = Column(Numeric(4, 3), nullable=True)
    segments = Column(JSON, default=list)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    video = relationship("Video", back_populates="transcript")


class MetadataGeneration(Base):
    __tablename__ = "metadata_generations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    ai_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_preset = Column(String(50), default="balanced")
    tokens_prompt = Column(Integer, default=0)
    tokens_completion = Column(Integer, default=0)
    estimated_cost_usd = Column(Numeric(8, 5), default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    video = relationship("Video", back_populates="metadata_generations")
    titles = relationship("TitleCandidate", back_populates="metadata_generation", cascade="all, delete-orphan")
    description = relationship("DescriptionRecord", back_populates="metadata_generation", uselist=False, cascade="all, delete-orphan")
    tags = relationship("TagRecord", back_populates="metadata_generation", uselist=False, cascade="all, delete-orphan")


class TitleCandidate(Base):
    __tablename__ = "titles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    metadata_generation_id = Column(String(36), ForeignKey("metadata_generations.id", ondelete="CASCADE"), nullable=False)
    title_text = Column(String(255), nullable=False)
    reasoning = Column(Text, nullable=True)
    estimated_intent = Column(String(100), nullable=True)
    keywords = Column(JSON, default=list)
    character_length = Column(Integer, nullable=True)
    candidate_index = Column(Integer, nullable=False)
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    metadata_generation = relationship("MetadataGeneration", back_populates="titles")


class DescriptionRecord(Base):
    __tablename__ = "descriptions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    metadata_generation_id = Column(String(36), ForeignKey("metadata_generations.id", ondelete="CASCADE"), nullable=False, unique=True)
    short_description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=False)
    call_to_action = Column(Text, nullable=True)
    links_placeholder = Column(Text, nullable=True)
    hashtags = Column(JSON, default=list)
    chapters = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    metadata_generation = relationship("MetadataGeneration", back_populates="description")


class TagRecord(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    metadata_generation_id = Column(String(36), ForeignKey("metadata_generations.id", ondelete="CASCADE"), nullable=False, unique=True)
    primary_keywords = Column(JSON, default=list)
    secondary_keywords = Column(JSON, default=list)
    long_tail_keywords = Column(JSON, default=list)
    combined_tags_string = Column(Text, nullable=True)
    tag_count = Column(Integer, default=0)
    total_character_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    metadata_generation = relationship("MetadataGeneration", back_populates="tags")


class ThumbnailRecord(Base):
    __tablename__ = "thumbnails"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    metadata_generation_id = Column(String(36), ForeignKey("metadata_generations.id", ondelete="SET NULL"), nullable=True)
    concept_title = Column(String(255), nullable=True)
    text_suggestions = Column(Text, nullable=True)
    visual_composition = Column(Text, nullable=True)
    subject_placement = Column(Text, nullable=True)
    background_concept = Column(Text, nullable=True)
    local_file_path = Column(Text, nullable=True)
    storage_url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)
    width = Column(Integer, default=1280)
    height = Column(Integer, default=720)
    is_generated = Column(Boolean, default=False)
    is_selected = Column(Boolean, default=False)
    is_uploaded_to_youtube = Column(Boolean, default=False)
    status = Column(String(50), default="DRAFT")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="thumbnails")


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(50), default="QUEUED", nullable=False)
    progress_percent = Column(Numeric(5, 2), default=0.0)
    bytes_uploaded = Column(BigInteger, default=0)
    total_bytes = Column(BigInteger, default=0)
    scheduled_for = Column(DateTime, nullable=True)
    privacy_status = Column(String(50), default="private")
    playlist_id = Column(String(100), nullable=True)
    made_for_kids = Column(Boolean, default=False)
    notify_subscribers = Column(Boolean, default=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    last_error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="upload_jobs")
    attempts = relationship("UploadAttempt", back_populates="upload_job", cascade="all, delete-orphan")


class UploadAttempt(Base):
    __tablename__ = "upload_attempts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    upload_job_id = Column(String(36), ForeignKey("upload_jobs.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    bytes_sent = Column(BigInteger, default=0)
    http_status_code = Column(Integer, nullable=True)
    response_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(8, 2), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    upload_job = relationship("UploadJob", back_populates="attempts")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    snapshot_date = Column(DateTime, nullable=False)
    period_type = Column(String(50), nullable=False)  # day, week, 28day, 90day, lifetime
    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    shares = Column(BigInteger, default=0)
    subscribers_gained = Column(Integer, default=0)
    subscribers_lost = Column(Integer, default=0)
    watch_time_minutes = Column(Numeric(12, 2), default=0.0)
    average_view_duration_seconds = Column(Numeric(8, 2), default=0.0)
    average_view_percentage = Column(Numeric(5, 2), default=0.0)
    impressions = Column(BigInteger, default=0)
    click_through_rate = Column(Numeric(5, 2), default=0.0)
    estimated_revenue_usd = Column(Numeric(10, 2), default=0.0)
    created_at = Column(DateTime, default=utcnow)


class ChannelInsight(Base):
    __tablename__ = "channel_insights"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    query_text = Column(Text, nullable=True)
    insight_type = Column(String(50), nullable=True)
    data_basis = Column(JSON, nullable=False, default=dict)
    interpretation = Column(Text, nullable=False)
    actionable_suggestions = Column(JSON, nullable=False, default=list)
    confidence_rating = Column(String(20), default="HIGH")
    created_at = Column(DateTime, default=utcnow)


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    topic = Column(String(255), nullable=False)
    title_concept = Column(String(255), nullable=False)
    hook = Column(Text, nullable=True)
    video_structure = Column(Text, nullable=True)
    target_audience = Column(String(255), nullable=True)
    production_difficulty = Column(String(50), default="Medium")
    estimated_length_minutes = Column(Integer, default=10)
    status = Column(String(50), default="IDEA")
    source_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class ContentCalendar(Base):
    __tablename__ = "content_calendar"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    scheduled_datetime = Column(DateTime, nullable=False)
    status = Column(String(50), default="DRAFT")
    color_code = Column(String(20), default="#3B82F6")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AutomationSettings(Base):
    __tablename__ = "automation_settings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True, unique=True)
    folder_monitoring = Column(Boolean, default=True)
    ai_analysis = Column(Boolean, default=True)
    metadata_generation = Column(Boolean, default=True)
    thumbnail_generation = Column(Boolean, default=True)
    approval_required = Column(Boolean, default=True)
    auto_upload = Column(Boolean, default=False)
    auto_scheduling = Column(Boolean, default=False)
    analytics_sync = Column(Boolean, default=True)
    ai_insights = Column(Boolean, default=True)
    watch_folder_root = Column(String(255), default="D:\\YT-Automation")
    default_ai_provider = Column(String(50), default="gemini")
    ai_cost_preset = Column(String(50), default="balanced")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    profile = relationship("Profile", back_populates="automation_settings")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="INFO")
    deep_link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    profile = relationship("Profile", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor_type = Column(String(50), default="USER")
    actor_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    job_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)
    progress_percent = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    payload = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
