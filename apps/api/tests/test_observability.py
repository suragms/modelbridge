"""Tests for Phase 3 observability features."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.request_log import (
    PRICING_SOURCE_MANUAL,
    PRICING_SOURCE_UNKNOWN,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    USAGE_SOURCE_ESTIMATED,
    USAGE_SOURCE_PROVIDER,
    USAGE_SOURCE_UNAVAILABLE,
)
from app.services.metrics import metrics_response, record_request
from app.services.pricing import PricingInfo, PricingRegistry
from app.services.token_estimator import CharacterBasedEstimator, estimate_message_tokens
from app.services.usage import generate_request_id, is_success_status

client = TestClient(app)


class TestRequestId:
    def test_generate_request_id_format(self):
        rid = generate_request_id()
        assert rid.startswith("req_")
        assert len(rid) > 10


class TestRequestStatus:
    def test_success_status_completed(self):
        assert is_success_status("COMPLETED")
        assert is_success_status("success")

    def test_failed_not_success(self):
        assert not is_success_status("FAILED")
        assert not is_success_status("error")


class TestTokenEstimator:
    def test_character_based_estimate(self):
        est = CharacterBasedEstimator()
        assert est.estimate("") == 0
        assert est.estimate("hello world") >= 1

    def test_estimate_message_tokens(self):
        inp, out = estimate_message_tokens([{"content": "Hello there"}])
        assert inp > 0
        assert out == 0

    def test_estimated_not_exact(self):
        """Estimates must be labeled as ESTIMATED, not provider-reported."""
        assert USAGE_SOURCE_ESTIMATED != USAGE_SOURCE_PROVIDER


class TestPricing:
    def test_calculate_cost_known_pricing(self):
        pricing = PricingInfo(1.0, 2.0, "USD", PRICING_SOURCE_MANUAL, is_known=True)
        inp, out, total, est = PricingRegistry.calculate_cost(1_000_000, 500_000, pricing)
        assert inp == pytest.approx(1.0)
        assert out == pytest.approx(1.0)
        assert total == pytest.approx(2.0)
        assert est is True

    def test_unknown_pricing_returns_zero(self):
        pricing = PricingInfo(0.0, 0.0, "USD", PRICING_SOURCE_UNKNOWN, is_known=False)
        inp, out, total, _ = PricingRegistry.calculate_cost(1000, 1000, pricing)
        assert inp == 0.0
        assert out == 0.0
        assert total == 0.0

    def test_local_model_no_fabricated_cost(self):
        pricing = PricingInfo(0.0, 0.0, "USD", PRICING_SOURCE_UNKNOWN, is_known=False)
        assert not pricing.is_known


class TestUsageSources:
    def test_usage_source_values(self):
        assert USAGE_SOURCE_PROVIDER == "PROVIDER_REPORTED"
        assert USAGE_SOURCE_ESTIMATED == "ESTIMATED"
        assert USAGE_SOURCE_UNAVAILABLE == "UNAVAILABLE"


class TestPrometheusMetrics:
    def test_metrics_endpoint(self):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "modelbridge_requests_total" in response.text

    def test_record_request_safe_labels(self):
        record_request(
            status=REQUEST_STATUS_COMPLETED,
            provider="ollama",
            duration_seconds=0.5,
            input_tokens=100,
            output_tokens=50,
        )
        body, _ = metrics_response()
        text = body.decode()
        assert "modelbridge_requests_total" in text
        assert "modelbridge_tokens_total" in text
        # No unbounded cardinality labels
        assert "request_id" not in text
        assert "user_id" not in text


class TestSecuritySanitization:
    def test_audit_sanitizes_secrets(self):
        from app.services.audit import _sanitize_metadata

        result = _sanitize_metadata({"api_key": "sk-secret", "name": "test"})
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"

    @pytest.mark.asyncio
    async def test_error_response_no_stack_trace(self):
        """Global handler must not expose internal details."""
        from starlette.requests import Request

        from app.main import global_exception_handler

        scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
        request = Request(scope)
        response = await global_exception_handler(request, RuntimeError("secret internal trace"))
        body = response.body.decode()
        assert "secret internal trace" not in body
        assert "INTERNAL_ERROR" in body


class TestRequestLifecycle:
    @pytest.mark.asyncio
    async def test_complete_request_sets_completed_at(self):
        from app.services.usage import UsageService

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        svc = UsageService(db)
        log = await svc.complete_request(
            request_id="req_test123",
            model="gpt-4",
            provider="openai",
            latency_ms=100.0,
            status=REQUEST_STATUS_COMPLETED,
            user_id=uuid.uuid4(),
        )
        assert log.status == REQUEST_STATUS_COMPLETED
        assert log.completed_at is not None

    @pytest.mark.asyncio
    async def test_failed_request(self):
        from app.services.usage import UsageService

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        svc = UsageService(db)
        log = await svc.complete_request(
            request_id="req_fail",
            model="gpt-4",
            provider="openai",
            latency_ms=50.0,
            status=REQUEST_STATUS_FAILED,
            error="timeout",
            error_type="PROVIDER_TIMEOUT",
        )
        assert log.status == REQUEST_STATUS_FAILED
        assert log.error_type == "PROVIDER_TIMEOUT"
