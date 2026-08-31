"""Risk classification with an explainable reason."""

from __future__ import annotations

from dataclasses import dataclass, field

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"

_CLASS_TO_RISK = {
    "GENERAL": RISK_LOW,
    "CODE": RISK_LOW,
    "FINANCIAL": RISK_MEDIUM,
    "PERSONAL_DATA": RISK_HIGH,
    "SENSITIVE": RISK_HIGH,
    "HIGH_RISK": RISK_CRITICAL,
}


@dataclass
class RiskResult:
    level: str
    reasons: list[str] = field(default_factory=list)


def classify_risk(
    *,
    classification: str,
    has_pii: bool = False,
    has_secret: bool = False,
    has_vision: bool = False,
    requested_model: str | None = None,
) -> RiskResult:
    reasons: list[str] = []
    level = _CLASS_TO_RISK.get(classification, RISK_LOW)
    reasons.append(f"Classification {classification} maps to {level}")

    if has_secret:
        level = RISK_CRITICAL
        reasons.append("Secret-like material detected")
    elif has_pii and level not in (RISK_HIGH, RISK_CRITICAL):
        level = RISK_HIGH
        reasons.append("PII indicators detected")

    if has_vision and level == RISK_LOW:
        level = RISK_MEDIUM
        reasons.append("Vision/multimodal content increases risk")

    if requested_model and requested_model.lower() in {"auto"}:
        reasons.append("Auto routing selected — risk still driven by content")

    return RiskResult(level=level, reasons=reasons)
