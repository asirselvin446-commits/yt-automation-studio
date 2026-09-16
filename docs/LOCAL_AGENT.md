# Local Windows Watcher Agent & Pipeline

## Overview
The Local Windows Agent is a background process powered by Python `watchdog` and `ffmpeg` that monitors a configured Windows directory structure.

## Folder Pipeline Architecture
```
D:\YT-Automation\  (Configurable in Settings)
 ├── INBOX\         <-- User drops or renders video files here
 ├── PROCESSING\    <-- Active media inspection and AI synthesis
 ├── APPROVED\      <-- Approved by creator, staged for upload
 ├── UPLOADING\     <-- Active upload in progress
 ├── UPLOADED\      <-- Successfully published to YouTube
 ├── FAILED\        <-- Inspection failure, rejected, or upload error
 ├── ARCHIVE\       <-- Post-upload cold storage
 ├── THUMBNAILS\    <-- Extracted frames and thumbnail concepts
 └── TEMP\          <-- Extracted audio chunks and processing cache
```

## Media Ingestion Steps
1. **File Drop Detection**: Watchdog observer detects newly appeared `.mp4`, `.mov`, `.mkv`, `.avi`, or `.webm` files.
2. **File Stability Check**: Checks file size across successive intervals and tests write locks to ensure the Windows Explorer copy/render process is 100% complete before opening.
3. **SHA-256 Deduplication**: Calculates a buffered SHA-256 hash. If an identical video was already ingested, it flags it as a duplicate and halts further processing.
4. **FFprobe Inspection**: Inspects duration, resolution, frame rate, video codec, audio codec, and audio channels.
5. **Relocation to PROCESSING**: Safely moves the media file into `PROCESSING\`.
6. **Backend Ingestion**: Calls `POST /api/v1/videos/internal-register` to create database records and trigger the AI pipeline.
