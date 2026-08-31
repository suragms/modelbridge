"""Webhook signing and verification."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from app.auth.encryption import decrypt_secret, encrypt_secret

SIGNATURE_VERSION = "v1"
TOLERANCE_SECONDS = 300


def generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_urlsafe(32)}"


def sign_payload(secret: str, payload: bytes, timestamp: int | None = None) -> str:
    ts = timestamp or int(time.time())
    signed = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},{SIGNATURE_VERSION}={signed}"


def verify_signature(secret: str, payload: bytes, signature_header: str) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        ts = int(parts["t"])
        sig = parts.get(SIGNATURE_VERSION, "")
    except (ValueError, KeyError):
        return False

    if abs(int(time.time()) - ts) > TOLERANCE_SECONDS:
        return False

    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def encrypt_webhook_secret(secret: str) -> str:
    return encrypt_secret(secret)


def decrypt_webhook_secret(encrypted: str) -> str:
    return decrypt_secret(encrypted)
