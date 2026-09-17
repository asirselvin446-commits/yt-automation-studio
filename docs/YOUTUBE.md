# YT Automation Studio — YouTube Integration

## Overview

YT Automation Studio integrates with YouTube via three Google APIs:
1. **YouTube Data API v3** — Channel management, video uploads, metadata
2. **YouTube Analytics API v2** — Channel and video metrics
3. **Google OAuth 2.0** — Secure authentication and token management

## OAuth 2.0 Flow

### Setup
1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable YouTube Data API v3 and YouTube Analytics API
3. Create OAuth 2.0 Client ID (Desktop application type)
4. Set redirect URI to `http://127.0.0.1:8000/api/v1/youtube/oauth2callback`
5. Add credentials to `.env`:
```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
YOUTUBE_API_KEY=your_api_key
```

### Token Lifecycle
- Access tokens expire after ~1 hour
- Refresh tokens are stored encrypted (Fernet) in the database
- Automatic token refresh before API calls
- Token revocation on channel disconnect

## Video Upload

### Resumable Upload Protocol
The uploader (`backend/app/integrations/youtube/uploader.py`) implements YouTube's resumable upload protocol:

1. **Initialize session** — POST metadata to get a resumable upload URI
2. **Upload chunks** — PUT 10 MB chunks with `Content-Range` headers
3. **Resume on failure** — Query upload status and continue from last byte
4. **Exponential backoff** — Retry with 1s, 2s, 4s, 8s... up to 64s delay

### Upload Parameters
| Parameter | Description | Default |
|:---|:---|:---|
| `privacy_status` | `private`, `unlisted`, `public` | `private` |
| `category_id` | YouTube category ID | `22` (People & Blogs) |
| `scheduled_publish_at` | ISO 8601 datetime for scheduled publish | None |
| `playlist_id` | Auto-add to playlist after upload | None |

### Supported Formats
`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.flv`, `.wmv`

## Analytics

### Available Metrics
- **Views** — Total video views
- **Watch Time** — Hours of watch time
- **Subscribers** — Gained and lost
- **Likes/Comments/Shares** — Engagement metrics
- **Average View Duration** — Retention indicator
- **Traffic Sources** — Where viewers come from
- **Demographics** — Age group and gender breakdown

### Time Ranges
| Code | Range |
|:---|:---|
| `today` | Current day |
| `7d` | Last 7 days |
| `28d` | Last 28 days |
| `90d` | Last 90 days |
| `lifetime` | All time |

## API Rate Limits

YouTube Data API v3 has a daily quota of **10,000 units**:
| Operation | Cost |
|:---|:---|
| Read (list, get) | 1 unit |
| Video upload | 1,600 units |
| Write (update, insert) | 50 units |
| Delete | 50 units |

The application tracks quota usage and warns when approaching limits.

## Disconnected State

When no YouTube channel is connected:
- All analytics show **zero** (no fake data)
- Upload queue is disabled
- Clear call-to-action prompts to connect a channel
- All other features (AI, inbox, processing) work normally
