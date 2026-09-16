import os
import time
from pathlib import Path
from typing import Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from agent.watcher.file_handler import wait_until_file_stable

SUPPORTED_EXTENSIONS: Set[str] = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


class VideoInboxHandler(FileSystemEventHandler):
    def __init__(self, on_video_ready: Callable[[str], None]):
        super().__init__()
        self.on_video_ready = on_video_ready
        self.processed_files: Set[str] = set()

    def _handle_path(self, file_path: str):
        path_obj = Path(file_path)
        if path_obj.is_dir() or path_obj.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        normalized = str(path_obj.resolve())
        if normalized in self.processed_files:
            return

        # Wait for write completion
        if wait_until_file_stable(normalized):
            self.processed_files.add(normalized)
            self.on_video_ready(normalized)

    def on_created(self, event):
        if not event.is_directory:
            self._handle_path(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._handle_path(event.dest_path)


class InboxWatcher:
    def __init__(self, inbox_dir: str, on_video_ready: Callable[[str], None]):
        self.inbox_dir = str(Path(inbox_dir).resolve())
        self.on_video_ready = on_video_ready
        self.observer = Observer()
        self.handler = VideoInboxHandler(on_video_ready)

    def scan_existing_files(self):
        """Scan INBOX for videos present before the watcher started."""
        if not os.path.exists(self.inbox_dir):
            return
        for item in os.listdir(self.inbox_dir):
            full_path = os.path.join(self.inbox_dir, item)
            if os.path.isfile(full_path):
                self.handler._handle_path(full_path)

    def start(self):
        Path(self.inbox_dir).mkdir(parents=True, exist_ok=True)
        self.scan_existing_files()
        self.observer.schedule(self.handler, self.inbox_dir, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
