# YT Automation Studio — Database Schema

## Overview

YT Automation Studio uses **Supabase PostgreSQL** as its primary database with a **local SQLite fallback** for offline/development operation. The schema contains **21 relational tables** covering the entire video automation lifecycle.

## Schema Migration

The primary schema is defined in `database/migrations/001_initial_schema.sql`.

### Applying to Supabase
```sql
-- Run via Supabase SQL Editor or psql
\i database/migrations/001_initial_schema.sql
```

### Seed Data
```sql
\i database/seed/seed_data.sql
```

## Entity Relationship Diagram

```
users ──┐
        ├── profiles
        ├── channels ── youtube_connections
        │       │
        │       ├── videos ──┬── video_files
        │       │            ├── video_analysis
        │       │            ├── transcripts
        │       │            ├── metadata_generations ──┬── titles
        │       │            │                         ├── descriptions  
        │       │            │                         └── tags
        │       │            ├── thumbnails
        │       │            ├── upload_jobs ── upload_attempts
        │       │            └── content_calendar
        │       │
        │       ├── analytics_snapshots
        │       └── channel_insights
        │
        ├── content_ideas
        ├── automation_settings
        ├── notifications
        └── audit_logs
```

## Table Reference

| Table | Purpose | Key Columns |
|:---|:---|:---|
| `users` | User accounts | id, email, created_at |
| `profiles` | Workspace preferences | user_id, display_name, theme |
| `channels` | YouTube channels | id, user_id, channel_id, title, subscriber_count |
| `youtube_connections` | Encrypted OAuth tokens | channel_id, access_token, refresh_token, token_expiry |
| `videos` | Master video record | id, title, status, publishing_mode, quality_status |
| `video_files` | File metadata | video_id, file_path, sha256_hash, duration, resolution |
| `video_analysis` | AI content analysis | video_id, transcript, topics, keywords, category |
| `transcripts` | Timestamped segments | video_id, start_time, end_time, text, confidence |
| `metadata_generations` | Versioned AI outputs | video_id, version, provider, tokens_used, cost |
| `titles` | Title candidates | generation_id, text, reasoning, is_selected |
| `descriptions` | Generated descriptions | generation_id, short, long, chapters, cta |
| `tags` | SEO tags | generation_id, primary, secondary, long_tail |
| `thumbnails` | Thumbnail concepts | video_id, concept, text_overlay, local_path |
| `upload_jobs` | Upload queue entries | video_id, channel_id, privacy_status, progress |
| `upload_attempts` | Granular upload logs | job_id, bytes_uploaded, error, timestamp |
| `analytics_snapshots` | Daily channel/video stats | channel_id, date, views, likes, watch_time |
| `channel_insights` | AI-generated insights | channel_id, content_type, insight_text |
| `content_ideas` | Idea lab storage | title, hook, structure, difficulty, status |
| `content_calendar` | Scheduling entries | video_id, scheduled_datetime, notes |
| `automation_settings` | Feature toggles | feature_name, is_enabled, value |
| `notifications` | In-app alerts | title, message, severity, is_read |
| `audit_logs` | Immutable action log | action, category, entity_type, entity_id |

## Video Status Lifecycle

```
INBOX → PROCESSING → READY_FOR_APPROVAL → APPROVED → UPLOADING → UPLOADED
                                        ↘ REJECTED
                            PROCESSING → FAILED
                            UPLOADING  → FAILED
```

## Indexes

Performance-critical indexes are created on:
- `videos(status)` — Status-based filtering
- `videos(channel_id, created_at)` — Channel video listing
- `video_files(sha256_hash)` — Duplicate detection
- `upload_jobs(status)` — Queue processing
- `analytics_snapshots(channel_id, snapshot_date)` — Time-series queries
- `audit_logs(created_at)` — Recent activity

## Row Level Security (RLS)

All tables in the `public` schema have RLS enabled. Policies enforce:
- Users can only access their own data via `auth.uid() = user_id`
- Service role bypasses RLS for backend operations
- `audit_logs` are insert-only (no updates or deletes)
