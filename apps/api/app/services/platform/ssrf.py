"""SSRF protection for outbound webhook URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import get_settings

BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"})


class SSRFError(ValueError):
    pass


def validate_webhook_url(url: str) -> str:
    settings = get_settings()
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"https", "http"}:
        raise SSRFError("URL must use http or https scheme")
    if settings.environment == "production" and parsed.scheme != "https":
        raise SSRFError("Production webhooks must use HTTPS")
    if not parsed.hostname:
        raise SSRFError("URL must include a hostname")
    host = parsed.hostname.lower()
    if host in BLOCKED_HOSTS:
        raise SSRFError("URL hostname is not allowed")
    if host.endswith(".local") or host.endswith(".internal"):
        raise SSRFError("Internal hostnames are not allowed")

    try:
        for info in socket.getaddrinfo(host, None):
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise SSRFError("URL resolves to a private or reserved address")
    except socket.gaierror as e:
        raise SSRFError(f"Cannot resolve hostname: {host}") from e

    return url.rstrip("/")
