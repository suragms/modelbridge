from __future__ import annotations

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()

_fernet: Fernet | None = None


def _derive_key(secret: str) -> bytes:
    """Derive a stable Fernet key (32-byte urlsafe base64) from a secret.

    Fernet keys must be exactly 32 bytes urlsafe-base64-encoded. Hashing the
    secret keeps the key deterministic so encrypted credentials remain
    decryptable across process restarts with the same configuration.
    """
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        if settings.encryption_key:
            # Explicitly configured ENCRYPTION_KEY — a raw Fernet key.
            key = settings.encryption_key.encode()
        elif settings.jwt_secret:
            # No encryption key configured: derive a stable key from the JWT
            # secret so encrypted credentials survive restarts. Admins should
            # set ENCRYPTION_KEY explicitly in production.
            key = _derive_key(settings.jwt_secret)
        else:
            key = Fernet.generate_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def generate_api_key() -> str:
    return f"mb_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_key_prefix(key: str) -> str:
    return key[:10] + "..."
