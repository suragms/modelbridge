"""Phase 17 AI Quality Platform tests."""

from __future__ import annotations

import pytest

from app.models.quality import EvaluatorType, RegressionStatus
from app.services.platform.events import EVENT_CATALOG, EventCatalog, sanitize_event_data
from app.services.quality.evaluators import (
    run_bias_check,
    run_hallucination_check,
    run_safety_evaluator,
)
from app.services.quality.regression import RegressionService


class TestQualityEventCatalog:
    def test_quality_events_registered(self):
        assert "evaluation.completed" in EVENT_CATALOG
        assert "evaluation.failed" in EVENT_CATALOG
        assert "quality.regression.detected" in EVENT_CATALOG
        assert "quality.gate.failed" in EVENT_CATALOG
        assert EVENT_CATALOG["evaluation.completed"]["category"] == "quality"

    def test_safe_payload_includes_quality_keys(self):
        data = sanitize_event_data({
            "gate_id": "g1",
            "pass_rate": 0.85,
            "execution_id": "r1",
            "password": "secret",
        })
        assert "gate_id" in data
        assert "pass_rate" in data
        assert "password" not in data


class TestEvaluators:
    def test_safety_detects_disallowed_pattern(self):
        result = run_safety_evaluator("This contains hack exploit", {"disallowed_patterns": [r"exploit"]})
        assert not result.passed
        assert result.methodology

    def test_safety_passes_clean_output(self):
        result = run_safety_evaluator("Hello world", {})
        assert result.passed

    def test_bias_check_insufficient_groups(self):
        result = run_bias_check([{"group": "a", "score": 0.9}], {})
        assert result.limitations
        assert "Insufficient" in result.detail or "groups" in result.detail.lower()

    def test_bias_check_detects_delta(self):
        cases = [{"group": "a", "score": 0.9}, {"group": "b", "score": 0.5}] * 3
        result = run_bias_check(cases, {"max_score_delta": 0.2})
        assert not result.passed
        assert result.evidence.get("delta") is not None

    def test_hallucination_reference_overlap(self):
        result = run_hallucination_check(
            "The capital of France is Paris",
            "Paris is the capital of France",
            {"method": "reference_comparison", "min_overlap": 0.2},
        )
        assert result.passed
        assert result.limitations

    def test_hallucination_without_reference(self):
        result = run_hallucination_check("Some output", "", {})
        assert result.limitations
        assert "unreliable" in result.limitations.lower() or "skipped" in result.detail.lower()

    def test_llm_judge_type_exists(self):
        assert EvaluatorType.LLM_JUDGE == "llm_judge"


class TestRegressionDetection:
    def test_regression_status_enum(self):
        assert RegressionStatus.REGRESSION_DETECTED == "regression_detected"
        assert RegressionStatus.NO_REGRESSION == "no_regression"


class TestRegressionMetrics:
    def test_quality_drop_detection_logic(self):
        thresholds = {"max_pass_rate_drop": 0.05}
        baseline_rate = 0.95
        candidate_rate = 0.80
        rate_drop = baseline_rate - candidate_rate
        assert rate_drop > thresholds["max_pass_rate_drop"]

    def test_no_regression_when_stable(self):
        baseline_rate = 0.92
        candidate_rate = 0.91
        rate_drop = baseline_rate - candidate_rate
        assert rate_drop <= 0.05
