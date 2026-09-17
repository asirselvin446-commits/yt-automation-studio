"""
YT Automation Studio — Desktop Application Launcher
Runs as a native Windows desktop software using Edge WebView2.
Embeds the FastAPI backend and Watchdog file observer.
"""
import sys
import os
import time
import threading
from pathlib import Path

# Determine base directory (handles both dev and PyInstaller frozen mode)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS).resolve()
    # Also add the app directory for .env loading
    APP_DIR = Path(os.path.dirname(sys.executable)).resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()
    APP_DIR = BASE_DIR

# Ensure backend module is importable
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))
sys.path.insert(0, str(APP_DIR))

# Set environment variable for .env file location
os.environ.setdefault("DOTENV_PATH", str(APP_DIR / "backend" / ".env"))

import uvicorn
import webview

# Import after paths are configured
from app.core.config import settings
from app.core.logging import system_logger


def run_backend_server():
    """Run FastAPI backend on local loopback."""
    try:
        # Change working directory so relative paths resolve correctly
        os.chdir(str(APP_DIR if getattr(sys, 'frozen', False) else BASE_DIR))

        from backend.main import app
        system_logger.info("Starting background FastAPI desktop server...")
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=settings.BACKEND_PORT,
            log_level="warning"
        )
    except Exception as e:
        system_logger.error(f"Backend server error: {e}")


def run_watcher_agent():
    """Run watchdog INBOX observer in background thread."""
    try:
        settings.ensure_directories()
        from agent.watcher.observer import InboxWatcher
        from agent.main import process_video_file
        watcher = InboxWatcher(str(settings.inbox_path), on_video_ready=process_video_file)
        watcher.start()
        system_logger.info(f"Background watcher agent active on: {settings.inbox_path}")
    except Exception as e:
        system_logger.error(f"Error starting watcher agent: {e}")


def get_icon_path():
    """Get the application icon path, checking multiple locations."""
    candidates = [
        BASE_DIR / "assets" / "icon.ico",
        APP_DIR / "assets" / "icon.ico",
        BASE_DIR / "assets" / "icon.png",
        APP_DIR / "assets" / "icon.png",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


class DesktopApi:
    """Bridge exposed to the web UI via pywebview (window.pywebview.api.*)."""

    def select_folder(self):
        """Open a native folder picker and return the chosen path (or None)."""
        try:
            windows = webview.windows
            if not windows:
                return None
            result = windows[0].create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                # pywebview returns a tuple/list of paths for folder dialogs.
                return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            system_logger.error(f"Folder dialog error: {e}")
        return None


def main():
    # 1. Start backend server in daemon thread
    server_thread = threading.Thread(target=run_backend_server, daemon=True)
    server_thread.start()

    # 2. Start folder watcher agent in daemon thread
    agent_thread = threading.Thread(target=run_watcher_agent, daemon=True)
    agent_thread.start()

    # Give backend a moment to boot
    time.sleep(1.5)

    # 3. Target URL (FastAPI serves compiled React dist)
    target_url = f"http://127.0.0.1:{settings.BACKEND_PORT}"

    # 4. Open native Windows desktop software window
    icon_path = get_icon_path()
    window = webview.create_window(
        title="YT Automation Studio",
        url=target_url,
        width=1400,
        height=900,
        min_size=(1024, 700),
        background_color="#090a0f",
        text_select=True,
        zoomable=True,
        js_api=DesktopApi()
    )

    # 5. Start GUI event loop — force Edge WebView2 (not Tkinter/MSHTML).
    # Never auto-open DevTools in the shipped (frozen) app — only in dev.
    dev_tools = settings.DEBUG and not getattr(sys, "frozen", False)
    try:
        webview.start(gui="edgechromium", debug=dev_tools)
    except Exception:
        # Fallback: let pywebview auto-detect best available renderer
        system_logger.warning("Edge WebView2 not available, using auto-detected renderer")
        webview.start(debug=dev_tools)


if __name__ == "__main__":
    main()
