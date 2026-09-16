import sys
import os
import time
import threading
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

import uvicorn
import webview
from app.core.config import settings
from app.core.logging import system_logger
from agent.main import InboxWatcher, process_video_file


def run_backend_server():
    """Run FastAPI backend on local loopback."""
    system_logger.info("Starting background FastAPI desktop server...")
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=settings.BACKEND_PORT,
        log_level="warning"
    )


def run_watcher_agent():
    """Run watchdog INBOX observer in background thread."""
    try:
        settings.ensure_directories()
        watcher = InboxWatcher(str(settings.inbox_path), on_video_ready=process_video_file)
        watcher.start()
        system_logger.info("Background watcher agent active.")
    except Exception as e:
        system_logger.error(f"Error starting watcher agent: {e}")


def main():
    # 1. Start backend server in daemon thread
    server_thread = threading.Thread(target=run_backend_server, daemon=True)
    server_thread.start()

    # 2. Start folder watcher agent in daemon thread
    agent_thread = threading.Thread(target=run_watcher_agent, daemon=True)
    agent_thread.start()

    # Give backend a moment to boot
    time.sleep(1.2)

    # 3. Target URL (FastAPI serves compiled React dist or dev proxy)
    target_url = f"http://127.0.0.1:{settings.BACKEND_PORT}"

    # 4. Open native Windows desktop software window
    window = webview.create_window(
        title="YT Automation Studio",
        url=target_url,
        width=1400,
        height=900,
        min_size=(1024, 700),
        background_color="#090a0f",
        text_select=True,
        zoomable=True
    )

    # 5. Start GUI event loop using native Edge WebView2 engine
    webview.start(gui="edgechromium", debug=settings.DEBUG)


if __name__ == "__main__":
    main()
