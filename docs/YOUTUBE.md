# YouTube Data & Analytics API Integration

## Google OAuth 2.0 Flow
YT Automation Studio uses standard Google OAuth 2.0 Web Application credentials.
Required Scopes:
- `https://www.googleapis.com/auth/youtube.upload`
- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/yt-analytics.readonly`

## Security Architecture
- Client secret and tokens are stored encrypted in the backend database using AES-256 Fernet encryption (`app.core.security`).
- Private OAuth tokens are **NEVER** transmitted to the browser or frontend client.

## Resumable Video Upload
Videos are uploaded via YouTube's official Resumable Upload protocol (`uploadType=resumable`), supporting:
- Large media files
- Chunked transmission
- Automatic retry with exponential backoff
- Thumbnail association (`thumbnails.set`)

## Zero-Fake Policy
In compliance with studio integrity requirements:
- The system never returns fake views, subscribers, or mock retention numbers.
- When disconnected, the UI explicitly prompts the user: *"Connect YouTube in Settings to view live channel analytics."*
