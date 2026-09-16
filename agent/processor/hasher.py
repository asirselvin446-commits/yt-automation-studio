import hashlib
from pathlib import Path


def calculate_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file using buffered chunks for memory efficiency."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()
