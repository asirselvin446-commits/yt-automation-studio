import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.core.config import settings
from app.core.logging import agent_logger
from agent.watcher.observer import InboxWatcher
from agent.processor.hasher import calculate_sha256
from agent.processor.ffmpeg_inspector import ffmpeg_inspector
from agent.services.backend_client import AgentBackendClient


def process_video_file(file_path: str):
    """Callback triggered when a stable video file is detected in INBOX."""
    agent_logger.info(f"Processing detected video: {file_path}")
    try:
        # 1. Compute SHA-256 hash for deduplication
        sha256 = calculate_sha256(file_path)
        agent_logger.info(f"Calculated SHA-256: {sha256}")

        # 2. Inspect with FFprobe
        meta = ffmpeg_inspector.inspect(file_path)
        if meta.get("is_corrupted"):
            agent_logger.error(f"File inspection failed or media corrupted: {file_path}")
            return

        # 3. Payload
        payload = {
            "source_path": file_path,
            "sha256_hash": sha256,
            "file_size_bytes": meta["file_size"],
            "duration_seconds": meta["duration"],
            "width": meta.get("width"),
            "height": meta.get("height"),
            "fps": meta.get("fps"),
            "video_codec": meta.get("video_codec"),
            "audio_codec": meta.get("audio_codec"),
            "has_audio": meta.get("has_audio", True)
        }

        # 4. Notify backend
        client = AgentBackendClient(backend_url=settings.BACKEND_URL)
        asyncio.run(client.notify_new_video(payload))

    except Exception as e:
        agent_logger.error(f"Error handling video {file_path}: {e}")


def main():
    agent_logger.info("Starting YT Automation Studio Windows Agent...")
    settings.ensure_directories()
    agent_logger.info(f"Monitoring INBOX folder: {settings.inbox_path}")

    watcher = InboxWatcher(str(settings.inbox_path), on_video_ready=process_video_file)
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        agent_logger.info("Windows Agent stopped.")


if __name__ == "__main__":
    main()
