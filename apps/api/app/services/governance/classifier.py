"""Heuristic request classification. Not a guarantee of accuracy."""

from __future__ import annotations

import re
from dataclasses import dataclass

CLASS_GENERAL = "GENERAL"
CLASS_CODE = "CODE"
CLASS_FINANCIAL = "FINANCIAL"
CLASS_PERSONAL_DATA = "PERSONAL_DATA"
CLASS_SENSITIVE = "SENSITIVE"
CLASS_HIGH_RISK = "HIGH_RISK"

_CODE = re.compile(
    r"\b(def |class |function |import |const |SELECT |FROM |```|console\.log)\b",
    re.I,
)
_FINANCIAL = re.compile(
    r"\b(iban|routing number|bank account|credit card|cvv|wire transfer|invoice amount)\b",
    re.I,
)
_PERSONAL = re.compile(
    r"\b(ssn|social security|passport|date of birth|home address|medical record)\b",
    re.I,
)
_SENSITIVE = re.compile(
    r"\b(classified|export controlled|attorney.?client|trade secret)\b",
    re.I,
)
_HIGH_RISK = re.compile(
    r"\b(exploit|malware|bypass authentication|build a bomb|child sexual)\b",
    re.I,
)


@dataclass
class ClassificationResult:
    classification: str
    reason: str
    heuristic: bool = True


def classify_request(text: str, *, has_pii: bool = False, has_secret: bool = False) -> ClassificationResult:
    """Configurable heuristic classifier. False positives/negatives are expected."""
    if has_secret or _HIGH_RISK.search(text):
        return ClassificationResult(CLASS_HIGH_RISK, "Secret or high-risk pattern detected")
    if has_pii or _PERSONAL.search(text):
        return ClassificationResult(CLASS_PERSONAL_DATA, "Personal-data indicators detected")
    if _SENSITIVE.search(text):
        return ClassificationResult(CLASS_SENSITIVE, "Sensitive-content indicators detected")
    if _FINANCIAL.search(text):
        return ClassificationResult(CLASS_FINANCIAL, "Financial indicators detected")
    if _CODE.search(text):
        return ClassificationResult(CLASS_CODE, "Code-like content detected")
    return ClassificationResult(CLASS_GENERAL, "No specialized indicators")
