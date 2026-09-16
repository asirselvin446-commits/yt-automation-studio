import os
import re
import secrets
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.config import settings


class SecurityService:
    def __init__(self):
        # Derive a 32-byte urlsafe base64 key from APP_SECRET_KEY
        key_bytes = hashlib.sha256(settings.APP_SECRET_KEY.encode()).digest()
        self._cipher = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt_secret(self, plaintext: str) -> str:
        """Encrypt sensitive strings such as OAuth tokens before storing."""
        if not plaintext:
            return ""
        return self._cipher.encrypt(plaintext.encode()).decode()

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decrypt encrypted secrets for internal worker usage."""
        if not ciphertext:
            return ""
        try:
            return self._cipher.decrypt(ciphertext.encode()).decode()
        except Exception:
            return ""

    def generate_oauth_state(self) -> str:
        """Generate a cryptographically secure state token for OAuth 2.0."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal and shell injection."""
        base = os.path.basename(filename)
        # Remove any path separators and unsafe characters
        sanitized = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', base)
        return sanitized.strip()

    @staticmethod
    def validate_safe_path(target_path: Path, allowed_root: Path) -> bool:
        """Ensure the target path is strictly contained within the allowed root directory."""
        try:
            resolved_target = target_path.resolve()
            resolved_root = allowed_root.resolve()
            return resolved_root in resolved_target.parents or resolved_target == resolved_root
        except Exception:
            return False


security = SecurityService()
