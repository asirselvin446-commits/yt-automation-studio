"""
YT Automation Studio — Desktop Application Launcher

Runs as a native Windows desktop app using Edge WebView2 (pywebview). It hosts
the FastAPI backend in a background thread and displays the compiled React UI
that the backend serves. Self-contained: no external Electron/Node runtime.
"""
import os
import sys
import time
import threading
from pathlib import Path

# Base dir handles both dev and PyInstaller-frozen modes.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS).resolve()
    APP_DIR = Path(os.path.dirname(sys.executable)).resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()
    APP_DIR = BASE_DIR

# Make the backend importable.
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))
sys.path.insert(0, str(APP_DIR))

import uvicorn
import webview

from app.core.config import settings
from app.core.logging import system_logger


def run_backend_server():
    """Run the FastAPI backend on local loopback."""
    try:
        os.chdir(str(APP_DIR if getattr(sys, "frozen", False) else BASE_DIR))
        from backend.main import app
        system_logger.info("Starting background FastAPI desktop server...")
        uvicorn.run(app, host="127.0.0.1", port=settings.BACKEND_PORT, log_level="warning")
    except Exception as e:
        system_logger.error(f"Backend server error: {e}")


def get_icon_path():
    for path in (
        BASE_DIR / "assets" / "icon.ico",
        APP_DIR / "assets" / "icon.ico",
        BASE_DIR / "assets" / "icon.png",
        APP_DIR / "assets" / "icon.png",
    ):
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
                return result[0] if isinstance(result, (list, tuple)) else result
        except Exception as e:
            system_logger.error(f"Folder dialog error: {e}")
        return None


def main():
    # 1. Start the backend (owns the cloud auto-upload pipeline) in a daemon thread.
    threading.Thread(target=run_backend_server, daemon=True).start()

    # Give the backend a moment to boot before pointing the window at it.
    time.sleep(1.5)

    target_url = f"http://127.0.0.1:{settings.BACKEND_PORT}"

    webview.create_window(
        title="YT Automation Studio",
        url=target_url,
        width=1400,
        height=900,
        min_size=(1024, 700),
        background_color="#090a0f",
        text_select=True,
        zoomable=True,
        js_api=DesktopApi(),
    )

    # Never auto-open DevTools in the shipped (frozen) app — only in dev.
    dev_tools = settings.DEBUG and not getattr(sys, "frozen", False)
    try:
        webview.start(gui="edgechromium", debug=dev_tools)
    except Exception:
        system_logger.warning("Edge WebView2 not available, using auto-detected renderer")
        webview.start(debug=dev_tools)


if __name__ == "__main__":
    main()
