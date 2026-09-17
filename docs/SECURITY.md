# YT Automation Studio — Security

## Overview

Security in YT Automation Studio follows the principle of **defense in depth** across all layers: authentication, data protection, API security, and file handling.

## Authentication & Authorization

### Google OAuth 2.0
- OAuth flow uses `state` parameter with HMAC signing to prevent CSRF
- Access tokens are short-lived (~1 hour) and auto-refreshed
- Refresh tokens are encrypted at rest using Fernet symmetric encryption
- Token revocation on channel disconnect

### API Security
- Backend API runs on `127.0.0.1` (loopback only) — not exposed to network
- CORS restricted to `localhost` origins
- Agent authentication via bearer token (`AGENT_AUTH_TOKEN`)
- No API keys or secrets in frontend bundle

## Data Protection

### Encryption at Rest
- OAuth refresh tokens: Fernet encryption via `cryptography` library
- Encryption key derived from `APP_SECRET_KEY`
- Local SQLite database file protected by OS file permissions

### Supabase (Cloud Mode)
- Row Level Security (RLS) enabled on all tables
- Policies enforce user-scoped data access via `auth.uid()`
- Service role key used only server-side (never in frontend)
- `audit_logs` table is insert-only (no UPDATE or DELETE policies)

## File Handling Security

### Path Traversal Prevention
- All file paths validated against the configured `YT_AUTOMATION_ROOT`
- Symlink resolution before path validation
- No user-supplied paths used in shell commands

### SHA-256 Integrity
- Every ingested video has a SHA-256 hash computed and stored
- Duplicate detection prevents re-processing of identical files
- Hash comparison available for uploaded file verification

## API Key Management

| Key | Storage | Exposure |
|:---|:---|:---|
| `SUPABASE_ANON_KEY` | `.env` (backend) + frontend `.env` | Client-safe (publishable) |
| `SUPABASE_SERVICE_ROLE_KEY` | `.env` (backend only) | Server-only |
| `GOOGLE_CLIENT_SECRET` | `.env` (backend only) | Server-only |
| `GEMINI_API_KEY` | `.env` (backend only) | Server-only |
| `OPENAI_API_KEY` | `.env` (backend only) | Server-only |
| `ANTHROPIC_API_KEY` | `.env` (backend only) | Server-only |
| `APP_SECRET_KEY` | `.env` (backend only) | Server-only |

## Best Practices

1. **Never commit `.env` files** — `.gitignore` excludes them
2. **Rotate `APP_SECRET_KEY`** — Invalidates all encrypted tokens
3. **Use Supabase RLS** — Even with backend validation, RLS is defense in depth
4. **Minimal OAuth scopes** — Only request YouTube API scopes needed
5. **Audit everything** — All API calls, file moves, and AI invocations are logged
6. **Human-in-the-loop** — `approval_required` is enabled by default; auto-upload is opt-in
