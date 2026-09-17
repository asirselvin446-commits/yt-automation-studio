"""Symmetric encryption for OAuth tokens at rest.

A Fernet key is derived from WORKER_SECRET_KEY exactly the way the desktop app's
SecurityService derives it, so the two stay compatible if the schemas are ever
unified. authorize.py encrypts the refresh token with this; the worker decrypts.
"""
import base64
import hashlib
from cryptography.fernet import Fernet

from config import config


def _cipher() -> Fernet:
    key_bytes = hashlib.sha256(config.WORKER_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _cipher().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return _cipher().decrypt(ciphertext.encode()).decode()
