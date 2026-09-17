"""Persistent, user-editable settings stored as a small JSON file.

The app's env-based `settings` are read-only config; this holds choices the user
makes in the UI at runtime (e.g. the custom upload folder) so they survive
restarts. Stored next to the app data dir, which works in both dev and the
packaged app.
"""
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict


def _settings_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(os.path.dirname(sys.executable))
    else:
        # backend/app/core/user_settings.py -> project root
        base = Path(__file__).resolve().parent.parent.parent.parent
    return base / "user_settings.json"


_PATH = _settings_path()
_lock = threading.Lock()


def load() -> Dict[str, Any]:
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_value(key: str, value: Any) -> None:
    with _lock:
        data = load()
        data[key] = value
        tmp = _PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _PATH)
