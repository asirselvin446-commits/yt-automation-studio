-- ==============================================================================
-- YT AUTOMATION STUDIO — DATABASE SCHEMA (SUPABASE POSTGRESQL)
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. USERS & PROFILES
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'creator' CHECK (role IN ('creator', 'editor', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 2. CHANNELS & YOUTUBE CONNECTIONS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    youtube_channel_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    custom_url TEXT,
    thumbnail_url TEXT,
    subscriber_count BIGINT DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    view_count BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.youtube_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    token_uri TEXT DEFAULT 'https://oauth2.googleapis.com/token',
    client_id TEXT,
    scopes TEXT[] DEFAULT ARRAY['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/yt-analytics.readonly'],
    expires_at TIMESTAMPTZ NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 3. VIDEOS MASTER TABLE
-- ------------------------------------------------------------------------------
-- Status workflow:
-- INBOX -> PROCESSING -> READY_FOR_APPROVAL -> APPROVED -> UPLOADING -> UPLOADED / FAILED / CANCELLED
CREATE TABLE IF NOT EXISTS public.videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INBOX' CHECK (
        status IN ('INBOX', 'PROCESSING', 'READY_FOR_APPROVAL', 'APPROVED', 'UPLOADING', 'UPLOADED', 'FAILED', 'CANCELLED')
    ),
    publishing_mode TEXT NOT NULL DEFAULT 'APPROVAL_REQUIRED' CHECK (
        publishing_mode IN ('APPROVAL_REQUIRED', 'AUTO_PUBLISH')
    ),
    quality_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (
        quality_status IN ('PENDING', 'READY', 'WARNING', 'BLOCKED', 'ERROR')
    ),
    source_path TEXT NOT NULL,
    current_folder_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    active_metadata_version INTEGER DEFAULT 1,
    scheduled_at TIMESTAMPTZ,
    uploaded_at TIMESTAMPTZ,
    youtube_video_id TEXT,
    youtube_url TEXT,
    privacy_status TEXT DEFAULT 'private' CHECK (privacy_status IN ('private', 'unlisted', 'public')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 4. VIDEO FILES (Media & Technical Inspection)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.video_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID UNIQUE REFERENCES public.videos(id) ON DELETE CASCADE,
    sha256_hash TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    duration_seconds NUMERIC(10, 3) NOT NULL,
    width INTEGER,
    height INTEGER,
    aspect_ratio TEXT,
    fps NUMERIC(6, 2),
    video_codec TEXT,
    video_bitrate BIGINT,
    has_audio BOOLEAN DEFAULT TRUE,
    audio_codec TEXT,
    audio_channels INTEGER,
    audio_sample_rate INTEGER,
    container_format TEXT,
    is_corrupted BOOLEAN DEFAULT FALSE,
    inspection_raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast duplicate detection by hash
CREATE INDEX IF NOT EXISTS idx_video_files_sha256 ON public.video_files(sha256_hash);

-- ------------------------------------------------------------------------------
-- 5. VIDEO ANALYSIS (Audio & AI Understanding)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.video_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID UNIQUE REFERENCES public.videos(id) ON DELETE CASCADE,
    audio_extracted_path TEXT,
    summary TEXT,
    topics TEXT[] DEFAULT '{}',
    keywords TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '[]',
    target_audience TEXT,
    content_category TEXT,
    important_moments JSONB DEFAULT '[]',
    raw_ai_payload JSONB,
    ai_provider TEXT,
    model_used TEXT,
    tokens_consumed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 6. TRANSCRIPTS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID UNIQUE REFERENCES public.videos(id) ON DELETE CASCADE,
    full_text TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    confidence NUMERIC(4, 3),
    segments JSONB DEFAULT '[]', -- [{ "start": 0.0, "end": 4.5, "text": "...", "confidence": 0.98 }]
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 7. METADATA GENERATIONS (Versioned AI Generations)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.metadata_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES public.videos(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    ai_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_preset TEXT DEFAULT 'balanced',
    tokens_prompt INTEGER DEFAULT 0,
    tokens_completion INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(8, 5) DEFAULT 0.00000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(video_id, version_number)
);

-- ------------------------------------------------------------------------------
-- 8. TITLES (5 candidates per generation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.titles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metadata_generation_id UUID REFERENCES public.metadata_generations(id) ON DELETE CASCADE,
    title_text TEXT NOT NULL,
    reasoning TEXT,
    estimated_intent TEXT,
    keywords TEXT[] DEFAULT '{}',
    character_length INTEGER,
    candidate_index INTEGER NOT NULL CHECK (candidate_index BETWEEN 1 AND 5),
    is_selected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 9. DESCRIPTIONS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metadata_generation_id UUID UNIQUE REFERENCES public.metadata_generations(id) ON DELETE CASCADE,
    short_description TEXT,
    long_description TEXT NOT NULL,
    call_to_action TEXT,
    links_placeholder TEXT,
    hashtags TEXT[] DEFAULT '{}',
    chapters JSONB DEFAULT '[]', -- [{ "timestamp": "00:00", "title": "Intro" }]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 10. TAGS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metadata_generation_id UUID UNIQUE REFERENCES public.metadata_generations(id) ON DELETE CASCADE,
    primary_keywords TEXT[] DEFAULT '{}',
    secondary_keywords TEXT[] DEFAULT '{}',
    long_tail_keywords TEXT[] DEFAULT '{}',
    combined_tags_string TEXT,
    tag_count INTEGER DEFAULT 0,
    total_character_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 11. THUMBNAILS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.thumbnails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES public.videos(id) ON DELETE CASCADE,
    metadata_generation_id UUID REFERENCES public.metadata_generations(id) ON DELETE SET NULL,
    concept_title TEXT,
    text_suggestions TEXT,
    visual_composition TEXT,
    subject_placement TEXT,
    background_concept TEXT,
    local_file_path TEXT,
    storage_url TEXT,
    preview_url TEXT,
    width INTEGER DEFAULT 1280,
    height INTEGER DEFAULT 720,
    is_generated BOOLEAN DEFAULT FALSE,
    is_selected BOOLEAN DEFAULT FALSE,
    is_uploaded_to_youtube BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'GENERATED', 'SELECTED', 'UPLOADED', 'REJECTED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 12. UPLOAD JOBS & ATTEMPTS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.upload_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES public.videos(id) ON DELETE CASCADE,
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN ('QUEUED', 'PROCESSING', 'READY_FOR_APPROVAL', 'APPROVED', 'UPLOADING', 'UPLOADED', 'FAILED', 'CANCELLED')
    ),
    progress_percent NUMERIC(5, 2) DEFAULT 0.00,
    bytes_uploaded BIGINT DEFAULT 0,
    total_bytes BIGINT DEFAULT 0,
    scheduled_for TIMESTAMPTZ,
    privacy_status TEXT DEFAULT 'private',
    playlist_id TEXT,
    made_for_kids BOOLEAN DEFAULT FALSE,
    notify_subscribers BOOLEAN DEFAULT TRUE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    last_error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.upload_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_job_id UUID REFERENCES public.upload_jobs(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    bytes_sent BIGINT DEFAULT 0,
    http_status_code INTEGER,
    response_payload JSONB,
    error_message TEXT,
    duration_seconds NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 13. ANALYTICS SNAPSHOTS (Time-series official data)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.analytics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    video_id UUID REFERENCES public.videos(id) ON DELETE SET NULL,
    snapshot_date DATE NOT NULL,
    period_type TEXT NOT NULL CHECK (period_type IN ('day', 'week', '28day', '90day', 'lifetime')),
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    subscribers_gained INTEGER DEFAULT 0,
    subscribers_lost INTEGER DEFAULT 0,
    watch_time_minutes NUMERIC(12, 2) DEFAULT 0.00,
    average_view_duration_seconds NUMERIC(8, 2) DEFAULT 0.00,
    average_view_percentage NUMERIC(5, 2) DEFAULT 0.00,
    impressions BIGINT DEFAULT 0,
    click_through_rate NUMERIC(5, 2) DEFAULT 0.00,
    estimated_revenue_usd NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(channel_id, video_id, snapshot_date, period_type)
);

-- ------------------------------------------------------------------------------
-- 14. CHANNEL INSIGHTS (Channel Brain AI Synthesis)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.channel_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    query_text TEXT,
    insight_type TEXT CHECK (insight_type IN ('performance_trend', 'topic_gap', 'retention_pattern', 'audience_behavior', 'custom_qa')),
    data_basis JSONB NOT NULL,
    interpretation TEXT NOT NULL,
    actionable_suggestions JSONB NOT NULL DEFAULT '[]',
    confidence_rating TEXT DEFAULT 'HIGH' CHECK (confidence_rating IN ('LOW', 'MEDIUM', 'HIGH')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 15. CONTENT IDEAS (Idea Lab)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.content_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    title_concept TEXT NOT NULL,
    hook TEXT,
    video_structure TEXT,
    target_audience TEXT,
    production_difficulty TEXT DEFAULT 'Medium' CHECK (production_difficulty IN ('Low', 'Medium', 'High')),
    estimated_length_minutes INTEGER DEFAULT 10,
    status TEXT DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'SCRIPT', 'IN_PRODUCTION', 'COMPLETED', 'ARCHIVED')),
    source_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 16. CONTENT CALENDAR
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.content_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES public.channels(id) ON DELETE CASCADE,
    video_id UUID REFERENCES public.videos(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    scheduled_datetime TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PROCESSING', 'READY', 'SCHEDULED', 'PUBLISHED')),
    color_code TEXT DEFAULT '#3B82F6',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 17. AUTOMATION SETTINGS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.automation_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE REFERENCES public.profiles(id) ON DELETE CASCADE,
    folder_monitoring BOOLEAN DEFAULT TRUE,
    ai_analysis BOOLEAN DEFAULT TRUE,
    metadata_generation BOOLEAN DEFAULT TRUE,
    thumbnail_generation BOOLEAN DEFAULT TRUE,
    approval_required BOOLEAN DEFAULT TRUE, -- Default strict safety
    auto_upload BOOLEAN DEFAULT FALSE,
    auto_scheduling BOOLEAN DEFAULT FALSE,
    analytics_sync BOOLEAN DEFAULT TRUE,
    ai_insights BOOLEAN DEFAULT TRUE,
    watch_folder_root TEXT DEFAULT 'D:\YT-Automation',
    default_ai_provider TEXT DEFAULT 'gemini',
    ai_cost_preset TEXT DEFAULT 'balanced' CHECK (ai_cost_preset IN ('low_cost', 'balanced', 'high_quality')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 18. NOTIFICATIONS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL CHECK (
        notification_type IN (
            'NEW_VIDEO_DETECTED',
            'PROCESSING_COMPLETE',
            'AI_ANALYSIS_COMPLETE',
            'APPROVAL_REQUIRED',
            'UPLOAD_STARTED',
            'UPLOAD_COMPLETED',
            'UPLOAD_FAILED',
            'ANALYTICS_SYNC_COMPLETED',
            'AUTH_EXPIRED',
            'SYSTEM_WARNING'
        )
    ),
    severity TEXT DEFAULT 'INFO' CHECK (severity IN ('INFO', 'SUCCESS', 'WARNING', 'ERROR')),
    deep_link TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 19. AUDIT LOGS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type TEXT DEFAULT 'USER' CHECK (actor_type IN ('USER', 'AGENT', 'AI_WORKER', 'YOUTUBE_WORKER', 'SYSTEM')),
    actor_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 20. GENERAL JOBS QUEUE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL CHECK (
        job_type IN ('VIDEO_ANALYSIS', 'TRANSCRIPTION', 'AI_METADATA', 'THUMBNAIL_GENERATION', 'UPLOAD', 'ANALYTICS_SYNC')
    ),
    resource_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    progress_percent INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    error_details JSONB,
    payload JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_videos_status ON public.videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON public.videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_status ON public.upload_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON public.jobs(status);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON public.notifications(profile_id, is_read);
CREATE INDEX IF NOT EXISTS idx_analytics_channel_date ON public.analytics_snapshots(channel_id, snapshot_date);

-- ------------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ------------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.youtube_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metadata_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.titles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.thumbnails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_calendar ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automation_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

-- Default authenticated read/write access policies (Supabase Auth)
CREATE POLICY "Users can access own profile" ON public.profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users can access own channels" ON public.channels FOR ALL USING (profile_id = auth.uid());
CREATE POLICY "Users can access own videos" ON public.videos FOR ALL USING (
    channel_id IN (SELECT id FROM public.channels WHERE profile_id = auth.uid()) OR channel_id IS NULL
);
CREATE POLICY "Users can access own automation settings" ON public.automation_settings FOR ALL USING (profile_id = auth.uid());
CREATE POLICY "Users can access own notifications" ON public.notifications FOR ALL USING (profile_id = auth.uid());
