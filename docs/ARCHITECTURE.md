# YT Automation Studio — Architecture

## Overview

YT Automation Studio is a **local-first**, **Windows-native** YouTube content automation and channel management platform. It runs as a standalone desktop application packaged via Inno Setup, with a bundled FastAPI backend, React frontend, and a Windows file watcher agent.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Desktop Application (WebView2)                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  React Frontend  │  │  FastAPI Backend  │  │ Watcher Agent │  │
│  │  (Vite + TS)     │  │  (Python 3.12)   │  │  (Watchdog)   │  │
│  │  Port: embedded  │  │  Port: 8000      │  │  Background   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │  HTTP/REST API      │                     │          │
│           └─────────────────────┘                     │          │
│                      │                                │          │
│           ┌──────────┴──────────┐          ┌─────────┴────────┐ │
│           │   Local SQLite DB   │          │  INBOX Directory  │ │
│           │   (Offline Mode)    │          │  (File Monitor)   │ │
│           └──────────┬──────────┘          └──────────────────┘ │
└──────────────────────┼──────────────────────────────────────────┘
                       │ (When Online)
              ┌────────┴────────┐
              │  Supabase Cloud  │
              │  (PostgreSQL)   │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
   ┌─────┴─────┐ ┌────┴────┐ ┌─────┴──────┐
   │  YouTube   │ │   AI    │ │  YouTube   │
   │  Data API  │ │Providers│ │ Analytics  │
   │   v3       │ │(4 opts) │ │    API     │
   └───────────┘ └─────────┘ └────────────┘
```

## Component Breakdown

### Frontend (`frontend/`)
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS with dark-first design
- **Icons**: Lucide React
- **Routing**: React Router v6
- **14 pages**: Dashboard, Inbox, Processing, Upload Queue, Videos, Video Detail, Calendar, Thumbnails, Ideas, Analytics, Channel Brain, Monetization, Automation, Settings

### Backend (`backend/`)
- **Framework**: FastAPI with async support
- **ORM**: SQLAlchemy 2.0 (async) with dual-engine support (Supabase PostgreSQL + local SQLite)
- **Validation**: Pydantic v2
- **10 API route groups**: system, videos, youtube, analytics, brain, ideas, calendar, monetization, automation, settings
- **AI Engine**: 4-provider abstraction (Gemini, OpenAI, Anthropic, Local/Ollama)
- **YouTube Integration**: OAuth 2.0, Data API v3, resumable uploader, Analytics API

### Agent (`agent/`)
- **Watcher**: Watchdog file system observer monitoring INBOX for video files
- **Stability Checker**: Polls file size to ensure copy completion before processing
- **FFprobe Inspector**: Extracts video metadata (duration, resolution, codecs)
- **SHA-256 Hasher**: Deduplication via content hashing
- **Frame Extractor**: FFmpeg-based thumbnail candidate extraction
- **Folder Manager**: Automated file movement across pipeline directories
- **Offline Queue**: SQLite-backed resilience for offline operation

### Desktop Shell (`desktop_app.py`)
- **Window**: Native 1400×900 window via Microsoft Edge WebView2
- **Embedded Server**: FastAPI runs in background daemon thread
- **Embedded Agent**: Watchdog observer in background daemon thread
- **Packaging**: PyInstaller → Inno Setup installer

## Data Flow

1. **Ingest**: Video dropped into INBOX → Watcher detects → Stability check → Move to PROCESSING
2. **Inspect**: FFprobe extracts metadata → SHA-256 hash computed → Dedup check
3. **AI Pipeline**: Transcript → Content analysis → 5 titles → Description → Tags → Thumbnail concepts
4. **Approval**: Video moves to READY_FOR_APPROVAL → Human reviews in UI → Approve/Reject
5. **Upload**: APPROVED → Resumable chunked upload to YouTube → UPLOADED
6. **Analytics**: Periodic sync of YouTube Analytics data → Dashboard visualization

## Security

- OAuth tokens encrypted at rest via `cryptography.fernet`
- API keys never exposed to frontend bundle
- Row Level Security (RLS) on all Supabase tables
- CORS restricted to localhost origins in production
- SHA-256 file integrity verification
