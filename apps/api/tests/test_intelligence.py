"""Phase 13 intelligence layer tests."""

from __future__ import annotations

import uuid

from app.models.intelligence import AutomationLevel, RecommendationStatus
from app.services.intelligence.anomalies import AnomalyService
from app.services.intelligence.assistant import OperationsAssistant
from app.services.intelligence.data_quality import MIN_SAMPLES_FORECAST, assess_quality
from app.services.intelligence.forecasting import ForecastingService
from app.services.intelligence.recommendations import RecommendationService


class TestDataQuality:
    def test_insufficient_data(self):
        q = assess_quality(sample_size=2, min_samples=10)
        assert q.status == "insufficient_data"
        assert q.confidence < 0.5

    def test_sufficient_data(self):
        q = assess_quality(sample_size=50, min_samples=10)
        assert q.status == "sufficient"
        assert q.confidence > 0.5

    def test_partial_with_missing(self):
        q = assess_quality(sample_size=20, min_samples=10, missing=["cost_records"])
        assert q.status == "partial"
        assert "cost_records" in q.missing_data


class TestForecasting:
    def test_linear_forecast_empty(self):
        svc = ForecastingService(None)  # type: ignore[arg-type]
        val, trend = svc._linear_forecast([], 7)
        assert val == 0.0
        assert trend == 0.0

    def test_linear_forecast_trend(self):
        svc = ForecastingService(None)  # type: ignore[arg-type]
        values = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0]
        val, trend = svc._linear_forecast(values, 1)
        assert trend > 0
        assert val >= values[-1]

    def test_min_samples_constant(self):
        assert MIN_SAMPLES_FORECAST >= 7


class TestAnomalyDetection:
    def test_zscore_no_anomaly_on_stable_series(self):
        svc = AnomalyService(None)  # type: ignore[arg-type]
        series = [100.0] * 20
        result = svc._check_series(uuid.uuid4(), "latency_ms", series)
        assert result is None

    def test_zscore_detects_spike(self):
        svc = AnomalyService(None)  # type: ignore[arg-type]
        series = [float(100 + (i % 3)) for i in range(19)] + [500.0]
        result = svc._check_series(uuid.uuid4(), "latency_ms", series)
        assert result is not None
        assert result.severity in {"low", "medium", "high", "critical"}

    def test_severity_escalates_with_z(self):
        svc = AnomalyService(None)  # type: ignore[arg-type]
        assert svc._severity(4.5, "latency_ms", 500, 100) == "critical"
        assert svc._severity(2.6, "latency_ms", 150, 100) == "low"


class TestAssistantClassification:
    def test_latency_intent(self):
        a = OperationsAssistant(None)  # type: ignore[arg-type]
        assert a._classify("why did latency increase?") == "latency"

    def test_spending_intent(self):
        a = OperationsAssistant(None)  # type: ignore[arg-type]
        assert a._classify("where is most of our AI spending?") == "spending"

    def test_unknown_intent(self):
        a = OperationsAssistant(None)  # type: ignore[arg-type]
        assert a._classify("tell me a joke") == "unknown"


class TestRecommendationLifecycle:
    def test_status_enum_values(self):
        assert RecommendationStatus.OPEN == "open"
        assert RecommendationStatus.APPROVED == "approved"

    def test_automation_levels(self):
        assert AutomationLevel.RECOMMEND == "recommend"
        assert AutomationLevel.OBSERVE_ONLY == "observe_only"
