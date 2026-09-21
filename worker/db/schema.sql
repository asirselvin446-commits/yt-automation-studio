-- ============================================================================
-- YT Automation Studio — Cloud Worker schema (Supabase / Postgres)
-- Run this once in the Supabase SQL editor.
--
-- Flow: the laptop uploads each video to Supabase Storage and inserts a QUEUED
-- row here; GitHub Actions uploads it to YouTube, then deletes the storage
-- object; the laptop later deletes the local file. So Supabase only ever holds
-- videos that are mid-flight, keeping storage usage near zero.
-- ============================================================================

-- Google OAuth credentials the worker acts with (YouTube upload).
-- Populated once by authorize.py. The refresh token is Fernet-encrypted with a
-- key derived from WORKER_SECRET_KEY, so the raw token never sits in the DB.
create table if not exists worker_credentials (
    id                       text primary key default 'google',
    refresh_token_encrypted  text not null,
    scopes                   text[] default '{}',
    youtube_channel_id       text,
    youtube_channel_title    text,
    updated_at               timestamptz not null default now()
);

-- One row per video. Job queue + de-duplication ledger + cleanup bookkeeping.
--   QUEUED -> PROCESSING -> UPLOADED   (happy path)
--                        -> FAILED     (retryable up to max attempts)
--                        -> SKIPPED    (duplicate content hash)
create table if not exists ingest_items (
    id                text primary key default gen_random_uuid()::text,
    file_name         text not null,
    -- where the bytes live at each stage
    local_path        text,              -- path on the laptop it came from
    storage_path      text,              -- object path in the Supabase Storage bucket
    mime_type         text,
    size_bytes        bigint default 0,
    sha256            text unique,       -- content fingerprint => never process the same video twice
    status            text not null default 'QUEUED',
    attempts          int  not null default 0,
    -- cleanup flags
    storage_deleted   boolean not null default false,  -- object removed after YouTube upload
    local_deleted     boolean not null default false,  -- laptop file removed after success
    -- publishing controls
    visibility        text default 'public',   -- public | unlisted | private
    publish_at        timestamptz,             -- scheduled go-public time (drip)
    -- results
    transcript        text,
    ai_metadata       jsonb,
    youtube_video_id  text,
    youtube_url       text,
    error             text,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

create index if not exists ingest_items_status_idx on ingest_items (status);

-- If you created the table before these columns existed, run once:
--   alter table ingest_items add column if not exists visibility text default 'public';
--   alter table ingest_items add column if not exists publish_at timestamptz;

-- ============================================================================
-- Auto-source content engine
-- ----------------------------------------------------------------------------
-- The desktop app writes ONE config row; GitHub Actions reads it and generates
-- + uploads videos on a schedule (works with the laptop off). Every generation
-- writes a row into autosource_runs so the app can show live status.
-- ============================================================================
create table if not exists autosource_config (
    id            text primary key default 'default',
    enabled       boolean not null default false,
    niche         text    not null default 'amazing facts',
    per_day       int     not null default 1,   -- videos generated per day (1-8)
    format        text    not null default 'shorts',  -- shorts (9:16) | landscape (16:9)
    provider      text    not null default 'edge',  -- edge | fish
    voice         text    default '',           -- edge-tts voice, e.g. en-US-AriaNeural
    fish_api_key  text    default '',           -- optional Fish Audio key (nicer voice)
    fish_voice    text    default '',           -- optional Fish reference/voice id
    pexels_api_key text   default '',           -- free Pexels key for stock B-roll video
    updated_at    timestamptz not null default now()
);

-- If you created autosource_config before these columns existed, run once:
--   alter table autosource_config add column if not exists format text not null default 'shorts';
--   alter table autosource_config add column if not exists pexels_api_key text default '';

create table if not exists autosource_runs (
    id                text primary key default gen_random_uuid()::text,
    status            text not null default 'RUNNING',  -- RUNNING | DONE | FAILED
    stage             text,                             -- human-readable live stage
    niche             text,
    topic             text,
    title             text,
    youtube_video_id  text,
    youtube_url       text,
    publish_at        timestamptz,
    error             text,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

create index if not exists autosource_runs_created_idx on autosource_runs (created_at desc);

alter table autosource_config enable row level security;
alter table autosource_runs   enable row level security;

-- ============================================================================
-- Row Level Security
-- ----------------------------------------------------------------------------
-- Enable RLS and add NO policies. With RLS on and no permissive policy, the
-- anon and authenticated (browser) keys can read/write nothing — important
-- because worker_credentials stores OAuth tokens. The worker uses the
-- service-role key, which ALWAYS bypasses RLS, so it keeps full access.
--
-- If you later want the desktop app / a dashboard to read progress with the
-- anon key, add a read-only policy, e.g.:
--   create policy "read ingest" on ingest_items for select to authenticated using (true);
-- Never add a policy that exposes worker_credentials.
-- ============================================================================
alter table worker_credentials enable row level security;
alter table ingest_items       enable row level security;
