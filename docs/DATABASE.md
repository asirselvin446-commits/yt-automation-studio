# YT Automation Studio — Database Schema & Architecture

## 1. Engine Decision: Supabase PostgreSQL
YT Automation Studio uses **Supabase PostgreSQL** as its primary production relational database, with an automatic local fallback (SQLite via `aiosqlite`) for offline desktop execution.

### Key Justifications
1. **Relational Integrity & Versioned Metadata**: Content automation requires deep relations:
   - `channels` -> `videos` -> `video_files` (technical media metadata & SHA-256 hash)
   - `videos` -> `transcripts` -> `metadata_generations` (v1, v2...)
   - `metadata_generations` -> `titles` (5 candidates), `descriptions`, `tags`, `thumbnails`
   - `upload_jobs` -> `upload_attempts`
2. **Channel Brain & Vector Search (`pgvector`)**:
   Enables semantic vector embeddings over video transcripts, titles, and viewer questions.
3. **Security & RLS (Row Level Security)**:
   Every table is secured with RLS policies, ensuring OAuth refresh tokens and creator data cannot be accessed across workspaces.

---

## 2. Table Catalog (21 Core Tables)

1. `profiles`: Creator user accounts and workspace preferences.
2. `channels`: Connected YouTube channels, title, statistics (subscribers, views, video count).
3. `youtube_connections`: Encrypted OAuth 2.0 access & refresh tokens, scopes, expiry.
4. `videos`: Master video records (`INBOX`, `PROCESSING`, `READY_FOR_APPROVAL`, `APPROVED`, `UPLOADING`, `UPLOADED`, `FAILED`, `CANCELLED`).
5. `video_files`: Media inspection details (SHA-256 hash, size, duration, width, height, fps, codecs, audio presence).
6. `video_analysis`: AI content summary, topics, keywords, entities, target audience, content category.
7. `transcripts`: Timestamped audio transcription segments.
8. `metadata_generations`: Versioned generations (`v1`, `v2`...) tracking tokens, cost, and provider.
9. `titles`: 5 candidate titles per generation with reasoning, estimated intent, and selection status.
10. `descriptions`: Short description, long description, CTA, links, hashtags, and chapter markers.
11. `tags`: Primary, secondary, and long-tail YouTube tags.
12. `thumbnails`: Visual layout concepts, text overlay suggestions, and preview URLs.
13. `upload_jobs`: YouTube upload queue entries, privacy status, playlist assignment, retry count.
14. `upload_attempts`: Granular attempt telemetry and error logs.
15. `analytics_snapshots`: Time-series channel and video metrics (views, watch time, subscribers).
16. `channel_insights`: Channel Brain synthesis separating data from interpretation and suggestions.
17. `content_ideas`: 10-idea lab entries with hook, structure, and difficulty.
18. `content_calendar`: Scheduled publishing events.
19. `automation_settings`: Feature toggles (folder monitoring, AI analysis, approval required, auto upload).
20. `notifications`: In-app notifications with severity ratings and deep links.
21. `audit_logs`: Immutable audit trails of all system, AI, and file actions.
22. `jobs`: General background job execution queue.
