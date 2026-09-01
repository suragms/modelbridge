"""Phase 18 AI FinOps tests."""

from __future__ import annotations

import pytest

from app.models.finops import ALLOWED_TAG_KEYS, CostType, SavingsStatus
from app.services.finops.engine import classify_cost_type
from app.services.finops.overview import validate_tags
from app.services.platform.events import EVENT_CATALOG
from app.services.pricing import PricingInfo, PricingRegistry


class TestCostTypes:
    def test_classify_estimated(self):
        assert classify_cost_type(is_estimated=True, pricing_source="provider") == CostType.ESTIMATED

    def test_classify_unknown(self):
        assert classify_cost_type(is_estimated=True, pricing_source="UNKNOWN") == CostType.UNKNOWN

    def test_classify_configured(self):
        assert classify_cost_type(is_estimated=False, pricing_source="manual") == CostType.CONFIGURED


class TestCostEngine:
    def test_calculate_cost_known_pricing(self):
        pricing = PricingInfo(1.0, 2.0, "USD", "manual", is_known=True)
        inp, out, total, est = PricingRegistry.calculate_cost(1000, 500, pricing)
        assert inp == pytest.approx(0.001)
        assert out == pytest.approx(0.001)
        assert total == pytest.approx(0.002)
        assert est is True

    def test_calculate_cost_unknown_pricing(self):
        pricing = PricingInfo(0, 0, "USD", "unknown", is_known=False)
        inp, out, total, est = PricingRegistry.calculate_cost(1000, 500, pricing)
        assert total == 0.0
        assert est is True


class TestTagValidation:
    def test_valid_tags(self):
        assert not validate_tags({"project": "alpha", "department": "eng"})

    def test_invalid_tag_key(self):
        errors = validate_tags({"invalid_key": "value"})
        assert any("Invalid tag key" in e for e in errors)

    def test_allowed_keys_defined(self):
        assert "project" in ALLOWED_TAG_KEYS
        assert "environment" in ALLOWED_TAG_KEYS


class TestFinopsEvents:
    def test_finops_events_registered(self):
        assert "budget.threshold.crossed" in EVENT_CATALOG
        assert "cost.anomaly.detected" in EVENT_CATALOG
        assert "optimization.recommendation.created" in EVENT_CATALOG


class TestSavingsStatus:
    def test_projected_not_measured(self):
        assert SavingsStatus.PROJECTED != SavingsStatus.MEASURED
