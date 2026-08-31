"""Safe redaction of detected spans. Original values are discarded."""

from __future__ import annotations

from typing import Callable, Protocol


class HasSpan(Protocol):
    category: str
    start: int
    end: int


_REPLACEMENTS = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "government_id": "[ID_REDACTED]",
    "payment": "[PAYMENT_REDACTED]",
    "credential": "[CREDENTIAL_REDACTED]",
    "secret": "[SECRET_REDACTED]",
}


def replacement_for(category: str) -> str:
    return _REPLACEMENTS.get(category, "[REDACTED]")


def redact_text(
    text: str,
    detections: list[HasSpan],
    replacement: Callable[[str], str] = replacement_for,
) -> str:
    if not detections:
        return text
    parts: list[str] = []
    cursor = 0
    for det in sorted(detections, key=lambda d: d.start):
        if det.start < cursor:
            continue
        parts.append(text[cursor : det.start])
        parts.append(replacement(det.category))
        cursor = det.end
    parts.append(text[cursor:])
    return "".join(parts)
