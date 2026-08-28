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

# Provider types that legitimately live on a local/private network. This
# includes the local providers (Ollama, LM Studio) and arbitrary user-defined
# OpenAI-compatible endpoints (custom), which are commonly served on localhost
# (LM Studio, vLLM, ...). Known cloud providers (openai, groq, openrouter,
# anthropic, gemini) are restricted to public hosts below.
_LOCAL_TYPES = {"ollama", "lmstudio", "custom"}

_ALLOWED_SCHEMES = {"http", "https"}


class InvalidURLError(ValueError):
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
    :class:`InvalidURLError` when the URL is unsafe or malformed for the provider
    type.
    """
    if not url or not url.strip():
        return None

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Unsupported URL scheme '{parsed.scheme or 'none'}'; only http and https are allowed"
        )

    if not parsed.hostname:
        raise InvalidURLError("Provider URL must include a host")

    if parsed.username or parsed.password:
        raise InvalidURLError("Provider URL must not embed credentials; supply the API key separately")

    host = parsed.hostname

    # Cloud-only types must not target a private/loopback host.
    if provider_type not in _LOCAL_TYPES:
        if _is_private_ip(host) or host == "localhost":
            raise InvalidURLError(f"URL host '{host}' is not allowed for provider type '{provider_type}'")

    # Guard against control characters / header injection.
    if re.search(r"[\r\n\t]", url):
        raise InvalidURLError("Provider URL contains invalid characters")

    # Rebuild netloc with a normalized (lowercased) host, preserving any port.
    port = f":{parsed.port}" if parsed.port else ""
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=f"{host.lower()}{port}",
    )
    return normalized.geturl().rstrip("/")
