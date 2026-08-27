"""Safe validation of provider endpoint URLs.

Protects against SSRF (Server-Side Request Forgery) and unsafe URLs when a
provider base URL is configured. Local provider types (Ollama, LM Studio) and
OpenAI-compatible custom endpoints are commonly served on localhost / private
networks, so those are allowed; cloud provider types are restricted to public,
HTTP(S) URLs only.

The gateway is self-hosted and providers are configured by authenticated
admins, so the primary goal here is to block the obvious unsafe cases:
non-HTTP schemes, embedded credentials, and literal private/loopback IPs when
they make no sense for the selected provider type.
"""

from __future__ import annotations

import ipaddress
import re

from urllib.parse import urlparse

# Provider types that legitimately live on a local/private network.
_LOCAL_TYPES = {"ollama", "lmstudio"}

# Provider types built on the OpenAI wire format; they may point at a local
# OpenAI-compatible server (LM Studio, vLLM, ...), so private hosts are allowed.
_COMPATIBLE_TYPES = {"lmstudio", "custom", "openai", "groq", "openrouter"}

_ALLOWED_SCHEMES = {"http", "https"}


class InvalidURL(ValueError):
    """Raised when a provider URL is rejected by validation."""


def _is_private_ip(host: str) -> bool:
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


def validate_provider_url(url: str | None, provider_type: str) -> str | None:
    """Validate and normalize a provider base URL.

    Returns the trimmed URL or ``None`` when no URL is supplied. Raises
    :class:`InvalidURL` when the URL is unsafe or malformed for the provider
    type.
    """
    if not url or not url.strip():
        return None

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise InvalidURL(
            f"Unsupported URL scheme '{parsed.scheme or 'none'}'; only http and https are allowed"
        )

    if not parsed.hostname:
        raise InvalidURL("Provider URL must include a host")

    if parsed.username or parsed.password:
        raise InvalidURL("Provider URL must not embed credentials; supply the API key separately")

    host = parsed.hostname

    # Cloud-only types must not target a private/loopback host.
    if provider_type not in _LOCAL_TYPES and provider_type not in _COMPATIBLE_TYPES:
        if _is_private_ip(host) or host == "localhost":
            raise InvalidURL(f"URL host '{host}' is not allowed for provider type '{provider_type}'")

    # Guard against control characters / header injection.
    if re.search(r"[\r\n\t]", url):
        raise InvalidURL("Provider URL contains invalid characters")

    normalized = parsed._replace(scheme=parsed.scheme.lower(), hostname=host.lower())
    return normalized.geturl().rstrip("/")
