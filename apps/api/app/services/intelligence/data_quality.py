"""Data quality assessment for intelligence analyses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


MIN_SAMPLES_PROVIDER = 10
MIN_SAMPLES_FORECAST = 7
MIN_SAMPLES_ANOMALY = 14


@dataclass
class DataQuality:
    status: str  # sufficient | insufficient_data | partial
    sample_size: int
    time_range_start: datetime | None
    time_range_end: datetime | None
    missing_data: list[str]
    confidence: float

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "sample_size": self.sample_size,
            "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
            "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
            "missing_data": self.missing_data,
            "confidence": round(self.confidence, 3),
        }


def assess_quality(
    *,
    sample_size: int,
    min_samples: int,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    missing: list[str] | None = None,
) -> DataQuality:
    missing = missing or []
    if sample_size < min_samples:
        confidence = max(0.0, sample_size / max(min_samples, 1) * 0.5)
        return DataQuality(
            status="insufficient_data",
            sample_size=sample_size,
            time_range_start=time_start,
            time_range_end=time_end,
            missing_data=missing + [f"need_at_least_{min_samples}_samples"],
            confidence=confidence,
        )
    confidence = min(1.0, 0.5 + (sample_size / (min_samples * 3)))
    if missing:
        return DataQuality(
            status="partial",
            sample_size=sample_size,
            time_range_start=time_start,
            time_range_end=time_end,
            missing_data=missing,
            confidence=confidence * 0.8,
        )
    return DataQuality(
        status="sufficient",
        sample_size=sample_size,
        time_range_start=time_start,
        time_range_end=time_end,
        missing_data=[],
        confidence=min(confidence, 0.95),
    )
