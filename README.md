# YT Automation Studio

> **Production-Ready Windows Desktop Software & Local-First YouTube Content Automation Workstation**

YT Automation Studio is a local-first YouTube automation and channel management platform designed for creators. When you drop a video into your local Windows `INBOX` folder, the software detects the file, extracts technical media metadata via FFmpeg, computes a SHA-256 hash for duplicate prevention, runs an AI understanding pipeline (5 title candidates, description with chapters, SEO tags, thumbnail concepts), and stages the video for creator approval.

---

## Key Features

- **Windows Desktop Software**: Native application window powered by Microsoft Edge WebView2, with background watcher agent and zero browser dependency.
- **Inno Setup Installer**: Complete setup executable (`YT-Automation-Studio-Setup.exe`) with desktop shortcuts and uninstaller.
- **Watched Folder Automation**: Continuous monitoring of `D:\YT-Automation\INBOX` (configurable to any drive or folder).
- **FFmpeg Inspection**: Real-time extraction of duration, resolution, frame rate, video/audio codecs, and container formats.
- **SHA-256 Duplicate Prevention**: Prevents duplicate media processing.
- **Multi-Provider AI Abstraction**: Pluggable support for **Google Gemini**, **OpenAI**, **Anthropic**, and **Local AI** (Ollama/vLLM).
- **Human Approval Required (Default)**: Strict safety model preventing unvetted publishing.
- **Official YouTube Data & Analytics API**: Real-time channel metrics and resumable chunked video uploads with zero fake stats.
- **AI Channel Brain**: Data-grounded insights strictly distinguishing *Data* from *Interpretation* from *Suggestions*.
- **Content Idea Lab**: 10-idea generator with first-15s hooks and outline structures.
- **Content Calendar & Monetization Tracker**: Official YouTube Partner Program progress evaluation.

---

## Project Structure

```
yt-automation-studio/
├── desktop_app.py              # Native Windows Desktop Software launcher
├── backend/                    # FastAPI server & business logic
│   ├── app/
│   │   ├── api/v1/             # 10 domain routers (videos, youtube, analytics, brain, etc.)
│   │   ├── core/               # Configuration, security ciphers, database engine, logging
│   │   ├── models/             # SQLAlchemy ORM schemas
│   │   ├── schemas/            # Pydantic DTO contracts
│   │   ├── services/           # Video lifecycle, quality checker, notifications
│   │   └── integrations/       # AI provider factory & YouTube OAuth client
│   └── main.py                 # FastAPI application entrypoint
├── agent/                      # Local Windows Watcher Agent
│   ├── watcher/                # Watchdog INBOX observer & file stability checker
│   ├── processor/              # FFmpeg inspector & SHA-256 hasher
│   └── main.py                 # Agent background runner
├── frontend/                   # React 18, TypeScript, Tailwind CSS, Lucide icons
│   ├── src/                    # 13 Studio pages & layout components
│   └── dist/                   # Production compiled desktop assets
├── installer/
│   ├── yt_automation_studio.iss# Inno Setup compiler configuration
│   └── output/                 # Generated YT-Automation-Studio-Setup.exe
├── database/
│   ├── migrations/             # Supabase PostgreSQL schema DDL (21 tables)
│   └── seed/                   # Seed data
├── docs/                       # Technical documentation
└── scripts/
    ├── build_software.py       # Full packaging pipeline (Vite + PyInstaller + Inno Setup)
    ├── build_installer.bat     # Windows batch script to compile the installer
    └── start_dev.bat           # Desktop software development runner
```

---

## Getting Started

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10+
- FFmpeg in Windows PATH (`ffmpeg` and `ffprobe`)
- Node.js 18+ (for building frontend)
- Inno Setup 6 (for compiling installer)

---

### Option 1: Running the Desktop Application in Development

1. **Activate Python Virtual Environment & Install Dependencies**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install -r backend\requirements.txt
   .\.venv\Scripts\pip install pywebview pyinstaller
   ```

2. **Build the Frontend UI**:
   ```powershell
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Launch the Native Desktop Software**:
   ```powershell
   .\scripts\start_dev.bat
   # Or directly:
   .\.venv\Scripts\python desktop_app.py
   ```
   A native desktop window will open with the complete YT Automation Studio workspace.

---

### Option 2: Compiling the Inno Setup Windows Installer

To build the standalone Windows installer (`YT-Automation-Studio-Setup.exe`):

```powershell
.\scripts\build_installer.bat
# Or:
.\.venv\Scripts\python scripts\build_software.py
```

The compiled installer is output to:
```
installer\output\YT-Automation-Studio-Setup.exe
```

---

## Configuration (`.env`)

Copy `.env.example` to `.env` and configure your credentials:

```env
# Database: Supabase PostgreSQL (or leave empty for local SQLite storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=sqlite+aiosqlite:///./data/yt_automation.db

# Google / YouTube OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/v1/youtube/oauth2callback

# AI Provider (Gemini / OpenAI / Anthropic / Local)
DEFAULT_AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
LOCAL_AI_BASE_URL=http://localhost:11434/v1

# Local Pipeline Root
YT_AUTOMATION_ROOT=./data/YT-Automation
```

---

## Documentation

- [Architecture & System Design](docs/ARCHITECTURE.md)
- [Database Schema & Supabase](docs/DATABASE.md)
- [Local Windows Watcher Agent](docs/LOCAL_AGENT.md)
- [YouTube OAuth & Resumable Uploads](docs/YOUTUBE.md)
- [AI Provider Abstraction](docs/AI.md)
- [Security & Path Protection](docs/SECURITY.md)
