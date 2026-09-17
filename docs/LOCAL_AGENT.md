# YT Automation Studio — Local Windows Agent

## Overview

The **Local Windows Agent** is a background process that monitors a configurable directory (INBOX) for new video files, inspects their metadata, computes integrity hashes, extracts thumbnail frames, and communicates with the FastAPI backend.

## Components

### 1. Inbox Watcher (`agent/watcher/observer.py`)
- Uses Python `watchdog` library to monitor the INBOX directory
- Detects `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm` file creation events
- Triggers processing pipeline on stable file detection

### 2. File Stability Checker (`agent/watcher/file_handler.py`)
- Polls file size at configurable intervals (default: 1s)
- Waits until size is stable for `STABLE_FILE_TIMEOUT_SECONDS` (default: 5s)
- Verifies no write locks remain by attempting a read
- Prevents processing of partially-copied files

### 3. FFprobe Inspector (`agent/processor/ffmpeg_inspector.py`)
- Extracts metadata using FFprobe:
  - Duration, resolution (width × height)
  - Frame rate (FPS)
  - Video codec (H.264, H.265, VP9, AV1)
  - Audio codec, channels, sample rate
  - File size, container format
- Detects corrupted files

### 4. SHA-256 Hasher (`agent/processor/hasher.py`)
- Computes SHA-256 hash of entire file
- Enables deduplication across the pipeline
- Hash stored in database for future reference

### 5. Frame Extractor (`agent/processor/frame_extractor.py`)
- Extracts evenly-spaced frames using FFmpeg
- Skips first/last 5% (intros/outros)
- Also supports keyframe (I-frame) extraction for scene changes
- Outputs 1920px-wide JPEG files

### 6. Folder Manager (`agent/services/folder_manager.py`)
- Manages the 9-directory pipeline structure:
  ```
  YT-Automation/
  ├── INBOX/          ← Drop videos here
  ├── PROCESSING/     ← Currently being analyzed
  ├── APPROVED/       ← Passed human review
  ├── UPLOADING/      ← Currently uploading to YouTube
  ├── UPLOADED/       ← Successfully uploaded
  ├── FAILED/         ← Processing or upload failed
  ├── ARCHIVE/        ← Long-term storage
  ├── THUMBNAILS/     ← Extracted thumbnail frames
  └── TEMP/           ← Intermediate processing files
  ```
- Handles filename conflicts with counter suffixes
- Atomic move operations with error handling

### 7. Offline Queue (`agent/services/offline_queue.py`)
- SQLite-backed queue for offline resilience
- Stores operations when backend is unreachable
- Automatic retry with exponential backoff (up to 5 retries)
- Dead-letter queue for permanently failed operations
- Purges completed items after 24 hours

### 8. Backend Client (`agent/services/backend_client.py`)
- HTTP client for agent → backend communication
- Bearer token authentication (`AGENT_AUTH_TOKEN`)
- Sends video ingestion payloads
- Reports processing status updates

## Configuration

```env
# Folder root (all pipeline directories created under this)
YT_AUTOMATION_ROOT=D:\YT-Automation

# Agent settings
AGENT_AUTH_TOKEN=your_secure_token
AGENT_POLL_INTERVAL_SECONDS=2
STABLE_FILE_TIMEOUT_SECONDS=5
```

## Running the Agent

### Standalone (Development)
```powershell
cd agent
python main.py
```

### As Part of Desktop App
The agent runs automatically as a daemon thread when the desktop app launches.

### As Windows Service (Advanced)
Can be configured via `sc create` or NSSM for always-on monitoring.

## Processing Pipeline

```
File dropped in INBOX
         │
         ▼
  Stability Check (wait for copy to complete)
         │
         ▼
  FFprobe Inspection (duration, codecs, resolution)
         │
         ▼
  SHA-256 Hash (deduplication check)
         │
         ▼
  Frame Extraction (6 thumbnail candidates)
         │
         ▼
  Move to PROCESSING directory
         │
         ▼
  Notify Backend (HTTP POST with metadata)
         │
         ▼
  AI Pipeline Triggers (backend handles from here)
```
