"""Baseline PII and secret detection (pattern-based).

This is heuristic detection, not a DLP product. False positives and false
negatives are expected. Matched values are never returned to callers of
audit helpers — only category labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.governance.redaction import redact_text, replacement_for


@dataclass
class Detection:
    category: str
    label: str
    confidence: str  # low | medium | high
    start: int
    end: int


# Patterns do not capture secret values into named groups used for logging.
_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("email", "Email", "high", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", "Phone Number", "medium", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")),
    ("government_id", "Government Identifier", "medium", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "payment",
        "Payment Information",
        "medium",
        re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    ),
    ("credential", "Password Assignment", "medium", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+")),
    ("secret", "PEM Private Key", "high", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("secret", "AWS Access Key", "high", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret", "GitHub Token", "high", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("secret", "Slack Token", "medium", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("secret", "JWT", "low", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("secret", "Generic API Key", "low", re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*\S{8,}")),
]

PII_CATEGORIES = frozenset({"email", "phone", "government_id", "payment"})
SECRET_CATEGORIES = frozenset({"secret", "credential"})


def detect_sensitive(text: str, *, pii: bool = True, secrets: bool = True) -> list[Detection]:
    if not text:
        return []
    found: list[Detection] = []
    for category, label, confidence, pattern in _PATTERNS:
        if category in PII_CATEGORIES and not pii:
            continue
        if category in SECRET_CATEGORIES and not secrets:
            continue
        for match in pattern.finditer(text):
            found.append(
                Detection(
                    category=category,
                    label=label,
                    confidence=confidence,
                    start=match.start(),
                    end=match.end(),
                )
            )
    found.sort(key=lambda d: d.start)
    return _dedupe_overlaps(found)


def _dedupe_overlaps(items: list[Detection]) -> list[Detection]:
    kept: list[Detection] = []
    last_end = -1
    for item in items:
        if item.start < last_end:
            continue
        kept.append(item)
        last_end = item.end
    return kept


def has_pii(detections: list[Detection]) -> bool:
    return any(d.category in PII_CATEGORIES for d in detections)


def has_secret(detections: list[Detection]) -> bool:
    return any(d.category in SECRET_CATEGORIES for d in detections)


def categories_only(detections: list[Detection]) -> list[str]:
    return sorted({d.label for d in detections})


def redact_with_detections(text: str, detections: list[Detection]) -> str:
    return redact_text(text, detections, replacement_for)
