# YT Automation Studio — Architecture & System Design

## 1. Overview
YT Automation Studio is a local-first desktop software application for Windows engineered to automate YouTube video ingestion, AI content analysis, metadata generation, and channel publishing with human-in-the-loop approval.

```
[ Local Windows Inbox Folder ]
             │ (Watchdog Observer)
             ▼
[ Windows Watcher Agent ] ──(FFmpeg & SHA-256)──> [ Technical Metadata ]
             │
             ▼ (FastAPI Internal API)
[ Dual-Engine Database (Supabase PostgreSQL / Local SQLite) ]
             │
             ▼
[ AI Provider Layer (Gemini, OpenAI, Anthropic, Local AI) ]
             │
             ├── 5 Title Candidates
             ├── Structured Description with Chapters
             ├── Primary, Secondary & Long-tail Tags
             └── Thumbnail Concepts
             │
             ▼
[ Quality Check Matrix & Human Approval Workstation ]
             │ (Creator Approves)
             ▼
[ YouTube Upload Queue & Resumable Uploader ]
             │
             ▼
[ Official YouTube Data & Analytics API Sync ]
             │
             ▼
[ AI Channel Brain & Content Idea Lab ]
```

## 2. Monorepo Components
- `desktop_app.py`: Desktop window shell powered by native Microsoft Edge WebView2 (`pywebview`). Boots the background server and watchdog agent silently without opening browser tabs or console windows.
- `backend/`: FastAPI backend with SQLAlchemy async models, Pydantic schemas, security ciphers, and 10 domain routers.
- `agent/`: Independent Windows background process running watchdog file monitoring, file stability verification, FFmpeg/FFprobe inspection, and SHA-256 hash calculation.
- `frontend/`: React 18, TypeScript, Tailwind CSS, Lucide icons, and modern studio dark UI compiled into production bundle in `frontend/dist`.
- `installer/`: Inno Setup compiler script (`yt_automation_studio.iss`) generating `YT-Automation-Studio-Setup.exe`.
- `database/`: Supabase PostgreSQL migrations with 21 relational tables and RLS policies.
