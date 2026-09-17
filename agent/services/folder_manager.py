"""
Folder Manager — Handles automated file movement across the
YT Automation Studio pipeline directories:
  INBOX → PROCESSING → APPROVED → UPLOADING → UPLOADED / FAILED / ARCHIVE
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import agent_logger


class FolderManager:
    """Manages the video file lifecycle across pipeline directories."""

    def __init__(self):
        self._ensure_all_dirs()

    def _ensure_all_dirs(self):
        """Create all pipeline directories if they don't exist."""
        settings.ensure_directories()

    def move_to_processing(self, source_path: str) -> Optional[str]:
        """Move a file from INBOX to PROCESSING."""
        return self._move_file(source_path, settings.processing_path, "PROCESSING")

    def move_to_approved(self, source_path: str) -> Optional[str]:
        """Move a file from PROCESSING to APPROVED."""
        return self._move_file(source_path, settings.approved_path, "APPROVED")

    def move_to_uploading(self, source_path: str) -> Optional[str]:
        """Move a file from APPROVED to UPLOADING."""
        return self._move_file(source_path, settings.uploading_path, "UPLOADING")

    def move_to_uploaded(self, source_path: str) -> Optional[str]:
        """Move a file from UPLOADING to UPLOADED after successful YouTube upload."""
        return self._move_file(source_path, settings.uploaded_path, "UPLOADED")

    def move_to_failed(self, source_path: str) -> Optional[str]:
        """Move a file to FAILED directory after processing/upload failure."""
        return self._move_file(source_path, settings.failed_path, "FAILED")

    def move_to_archive(self, source_path: str) -> Optional[str]:
        """Move a file to ARCHIVE for long-term storage."""
        return self._move_file(source_path, settings.archive_path, "ARCHIVE")

    def save_thumbnail(self, source_path: str, video_id: str) -> Optional[str]:
        """Save a thumbnail image to the THUMBNAILS directory with a video-specific prefix."""
        thumb_dir = settings.thumbnails_path / video_id
        thumb_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(source_path).name
        dest = thumb_dir / filename
        try:
            shutil.copy2(source_path, str(dest))
            agent_logger.info(f"Thumbnail saved: {dest}")
            return str(dest)
        except Exception as e:
            agent_logger.error(f"Failed to save thumbnail {source_path}: {e}")
            return None

    def get_temp_path(self, filename: str) -> str:
        """Get a path within the TEMP directory for intermediate processing."""
        return str(settings.temp_path / filename)

    def cleanup_temp(self, file_path: str) -> bool:
        """Remove a file from the TEMP directory."""
        try:
            path = Path(file_path)
            if path.exists() and str(settings.temp_path) in str(path.parent):
                path.unlink()
                agent_logger.debug(f"Cleaned up temp file: {file_path}")
                return True
        except Exception as e:
            agent_logger.error(f"Failed to clean temp file {file_path}: {e}")
        return False

    def get_pipeline_counts(self) -> dict:
        """Return file counts for each pipeline directory."""
        video_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv"}
        counts = {}
        for name, path in [
            ("inbox", settings.inbox_path),
            ("processing", settings.processing_path),
            ("approved", settings.approved_path),
            ("uploading", settings.uploading_path),
            ("uploaded", settings.uploaded_path),
            ("failed", settings.failed_path),
            ("archive", settings.archive_path),
        ]:
            try:
                if path.exists():
                    counts[name] = sum(
                        1 for f in path.iterdir()
                        if f.is_file() and f.suffix.lower() in video_extensions
                    )
                else:
                    counts[name] = 0
            except Exception:
                counts[name] = 0
        return counts

    @staticmethod
    def _move_file(source_path: str, dest_dir: Path, stage_name: str) -> Optional[str]:
        """
        Safely move a file to a destination directory.
        Handles filename conflicts by appending a counter suffix.
        """
        src = Path(source_path)
        if not src.exists():
            agent_logger.warning(f"Source file not found for {stage_name} move: {source_path}")
            return None

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        # Handle filename conflicts
        if dest.exists():
            stem = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            shutil.move(str(src), str(dest))
            agent_logger.info(f"Moved to {stage_name}: {src.name} → {dest}")
            return str(dest)
        except Exception as e:
            agent_logger.error(f"Failed to move {src.name} to {stage_name}: {e}")
            return None


# Singleton
folder_manager = FolderManager()
