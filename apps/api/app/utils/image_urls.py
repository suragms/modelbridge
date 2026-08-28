"""Validate vision image URLs without fetching them.

Protects against SSRF, dangerous schemes, embedded credentials, and oversized
data URIs. The gateway does not download arbitrary image URLs.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from fastapi import HTTPException

_ALLOWED_SCHEMES = {"https"}
_ALLOWED_DATA_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
# ~4 MB of base64 payload (before decode) — refuse larger inline images.
_MAX_DATA_URI_CHARS = 5_500_000
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


class UnsafeImageURLError(ValueError):
    """Raised when an image URL is rejected."""


def _is_private_host(host: str) -> bool:
    lowered = host.lower().rstrip(".")
    if lowered in _BLOCKED_HOSTS or lowered.endswith(".internal") or lowered.endswith(".local"):
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_image_url(url: str) -> str:
    """Return the URL if it is safe to pass through to a provider.

    Does not fetch the resource.
    """
    if not url or not url.strip():
        raise UnsafeImageURLError("Image URL is empty")
    url = url.strip()
    if re.search(r"[\r\n\t]", url):
        raise UnsafeImageURLError("Image URL contains invalid characters")

    if url.startswith("data:"):
        return _validate_data_uri(url)

    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeImageURLError(
            f"Unsupported image URL scheme '{parsed.scheme or 'none'}'; only https and data URIs are allowed"
        )
    if not parsed.hostname:
        raise UnsafeImageURLError("Image URL must include a host")
    if parsed.username or parsed.password:
        raise UnsafeImageURLError("Image URL must not embed credentials")
    if _is_private_host(parsed.hostname):
        raise UnsafeImageURLError("Image URL must not target a private or internal host")
    return url


def _validate_data_uri(url: str) -> str:
    # data:image/png;base64,<payload>
    header, _, payload = url.partition(",")
    meta = header[5:]  # strip "data:"
    mime = meta.split(";")[0].lower()
    if mime not in _ALLOWED_DATA_TYPES:
        raise UnsafeImageURLError(f"Unsupported image MIME type '{mime}'")
    if len(url) > _MAX_DATA_URI_CHARS:
        raise UnsafeImageURLError("Inline image exceeds the maximum allowed size")
    if payload and "base64" in meta.lower() and not re.fullmatch(r"[A-Za-z0-9+/=\s]+", payload[:2000]):
        raise UnsafeImageURLError("Inline image payload is not valid base64")
    return url


def validate_request_image_urls(urls: list[str]) -> None:
    try:
        for url in urls:
            validate_image_url(url)
    except UnsafeImageURLError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VISION_NOT_SUPPORTED",
                "message": str(exc),
                "type": "validation_error",
            },
        ) from exc
