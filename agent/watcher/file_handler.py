import time
import os
from pathlib import Path


def wait_until_file_stable(file_path: str, checks_required: int = 3, interval_sec: float = 1.0, max_wait_sec: float = 30.0) -> bool:
    """Ensure a file dropped in INBOX has finished being written by Windows Explorer/copy process."""
    start_time = time.time()
    last_size = -1
    consecutive_matches = 0

    while time.time() - start_time < max_wait_sec:
        if not os.path.exists(file_path):
            return False

        try:
            current_size = os.path.getsize(file_path)
            # Try opening in append mode to test if another process holds an exclusive write lock
            with open(file_path, "a+b"):
                pass
        except (OSError, PermissionError):
            # File is still locked by copying process
            consecutive_matches = 0
            time.sleep(interval_sec)
            continue

        if current_size == last_size and current_size > 0:
            consecutive_matches += 1
            if consecutive_matches >= checks_required:
                return True
        else:
            consecutive_matches = 0
            last_size = current_size

        time.sleep(interval_sec)

    return False
