"""
File Stability Handler — Ensures video files are completely written
before processing begins. Watches file size over multiple intervals 
to confirm the copy/download is complete and no write locks remain.
"""
import os
import time
from pathlib import Path
from app.core.logging import agent_logger


class FileStabilityChecker:
    """Verify a file has finished being written/copied before processing."""

    def __init__(self, stable_timeout: float = 5.0, check_interval: float = 1.0):
        """
        Args:
            stable_timeout: Seconds the file size must remain unchanged to be considered stable.
            check_interval: Seconds between size polls.
        """
        self.stable_timeout = stable_timeout
        self.check_interval = check_interval

    def wait_until_stable(self, file_path: str) -> bool:
        """
        Block until the file at `file_path` has a constant size for
        `stable_timeout` seconds. Returns True if the file is stable,
        False if the file vanished or an error occurred.
        """
        path = Path(file_path)
        if not path.exists():
            agent_logger.warning(f"File does not exist: {file_path}")
            return False

        last_size = -1
        stable_elapsed = 0.0
        max_wait = self.stable_timeout * 10  # absolute max wait before giving up
        total_waited = 0.0

        agent_logger.info(f"Waiting for file stability: {path.name} (timeout={self.stable_timeout}s)")

        while total_waited < max_wait:
            try:
                if not path.exists():
                    agent_logger.warning(f"File disappeared during stability check: {file_path}")
                    return False

                current_size = path.stat().st_size

                if current_size == last_size:
                    stable_elapsed += self.check_interval
                    if stable_elapsed >= self.stable_timeout:
                        # Double-check the file is not locked
                        if self._is_readable(file_path):
                            agent_logger.info(
                                f"File is stable: {path.name} ({current_size:,} bytes, "
                                f"stable for {stable_elapsed:.1f}s)"
                            )
                            return True
                        else:
                            agent_logger.debug(f"File size stable but still locked: {path.name}")
                            stable_elapsed = 0.0
                else:
                    if last_size >= 0:
                        agent_logger.debug(
                            f"File still writing: {path.name} "
                            f"({last_size:,} → {current_size:,} bytes)"
                        )
                    stable_elapsed = 0.0

                last_size = current_size
                time.sleep(self.check_interval)
                total_waited += self.check_interval

            except OSError as e:
                agent_logger.error(f"OS error during stability check for {file_path}: {e}")
                return False

        agent_logger.error(f"File stability timed out after {max_wait:.0f}s: {file_path}")
        return False

    @staticmethod
    def _is_readable(file_path: str) -> bool:
        """Attempt to open the file for reading to confirm no write locks."""
        try:
            with open(file_path, "rb") as f:
                f.read(1)
            return True
        except (IOError, PermissionError):
            return False


# Singleton instance
file_stability_checker = FileStabilityChecker()


def wait_until_file_stable(file_path: str) -> bool:
    """Module-level convenience wrapper delegating to the shared checker.

    Preserves the import contract used by ``agent.watcher.observer``.
    """
    return file_stability_checker.wait_until_stable(file_path)
