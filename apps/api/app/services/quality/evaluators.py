"""Evaluator execution with traceable methodology."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.models.quality import EvaluatorType
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.studio.evaluations import SCORERS, score_json_schema, score_regex


@dataclass
class EvaluatorResult:
    evaluator_name: str
    evaluator_type: str
    methodology: str
    passed: bool
    score: float | None
    detail: str
    limitations: str | None = None
    judge_model: str | None = None
    evidence: dict = field(default_factory=dict)


def _methodology_for(evaluator: dict) -> str:
    etype = evaluator.get("type", "rule")
    if etype == EvaluatorType.LLM_JUDGE:
        model = evaluator.get("config", {}).get("judge_model", "auto")
        return f"LLM-as-judge using model {model} — subjective; not objective truth"
    if etype == EvaluatorType.CUSTOM:
        return f"Custom evaluator {evaluator.get('name', 'unnamed')} v{evaluator.get('version', 1)}"
    if etype == EvaluatorType.REGEX:
        return "Pattern matching via regular expression"
    if etype == EvaluatorType.STRUCTURED_OUTPUT:
        return "JSON schema structural validation"
    return "Rule-based exact/contains match"


async def run_evaluator(
    evaluator: dict,
    *,
    actual: str,
    expected: str,
    input_text: str,
    db,
    user,
) -> EvaluatorResult:
    etype = evaluator.get("type", EvaluatorType.RULE)
    name = evaluator.get("name", etype)
    config = evaluator.get("config") or {}
    threshold = float(evaluator.get("threshold", config.get("threshold", 0.5)))
    methodology = _methodology_for(evaluator)

    if etype in (EvaluatorType.RULE, "exact_match"):
        fn = SCORERS.get(config.get("rule", "exact_match"), SCORERS["exact_match"])
        passed, detail = fn(actual, expected)
        return EvaluatorResult(name, etype, methodology, passed, 1.0 if passed else 0.0, detail)

    if etype == EvaluatorType.REGEX:
        pattern = config.get("pattern", expected)
        passed, detail = score_regex(actual, pattern)
        return EvaluatorResult(name, etype, methodology, passed, 1.0 if passed else 0.0, detail)

    if etype == EvaluatorType.STRUCTURED_OUTPUT:
        schema = config.get("schema", {})
        passed, detail = score_json_schema(actual, schema)
        return EvaluatorResult(name, etype, methodology, passed, 1.0 if passed else 0.0, detail)

    if etype == EvaluatorType.CUSTOM:
        rule_type = config.get("rule_type", "contains")
        fn = SCORERS.get(rule_type, SCORERS["contains"])
        target = config.get("target", expected)
        passed, detail = fn(actual, target)
        return EvaluatorResult(
            name,
            etype,
            methodology,
            passed,
            1.0 if passed else 0.0,
            detail,
            limitations="Custom rules are organization-defined; validate logic independently",
            evidence={"rule_type": rule_type, "version": evaluator.get("version", 1)},
        )

    if etype == EvaluatorType.LLM_JUDGE:
        return await _run_llm_judge(
            evaluator, name, config, threshold, actual, input_text, expected, db, user
        )

    return EvaluatorResult(name, etype, methodology, False, 0.0, f"Unknown evaluator type: {etype}")


async def _run_llm_judge(
    evaluator: dict,
    name: str,
    config: dict,
    threshold: float,
    actual: str,
    input_text: str,
    expected: str,
    db,
    user,
) -> EvaluatorResult:
    from app.services.gateway import execute_chat

    judge_model = config.get("judge_model", "auto")
    judge_prompt = config.get("evaluation_prompt") or (
        "You are an evaluation judge. Score the candidate output from 0.0 to 1.0 "
        "for task completion. Respond with JSON: {\"score\": float, \"reason\": string}."
    )
    scoring_schema = config.get("scoring_schema") or {"min": 0.0, "max": 1.0}

    messages = [
        ChatMessage(role="system", content=judge_prompt),
        ChatMessage(
            role="user",
            content=json.dumps({
                "input": input_text[:2000],
                "expected": expected[:1000] if expected else None,
                "actual": actual[:2000],
            }),
        ),
    ]

    try:
        result = await execute_chat(
            ChatCompletionRequest(model=judge_model, messages=messages, temperature=0, max_tokens=500),
            db,
            user,
            None,
        )
        raw = ""
        if result.response.choices:
            raw = result.response.choices[0].message.content or ""

        score = 0.0
        reason = raw[:500]
        try:
            parsed = json.loads(raw)
            score = float(parsed.get("score", 0.0))
            reason = str(parsed.get("reason", reason))
        except (json.JSONDecodeError, TypeError, ValueError):
            match = re.search(r"(\d+\.?\d*)", raw)
            if match:
                score = min(1.0, float(match.group(1)))

        passed = score >= threshold
        return EvaluatorResult(
            name,
            EvaluatorType.LLM_JUDGE,
            f"LLM-as-judge using {judge_model}",
            passed,
            score,
            reason,
            limitations=(
                "LLM judge scores are model-generated opinions, not objective measurements. "
                "Results vary by judge model and prompt."
            ),
            judge_model=result.selected_model or judge_model,
            evidence={
                "method": "llm_judge",
                "judge_model": result.selected_model or judge_model,
                "provider": result.provider,
                "scoring_schema": scoring_schema,
                "threshold": threshold,
            },
        )
    except Exception as e:
        return EvaluatorResult(
            name,
            EvaluatorType.LLM_JUDGE,
            f"LLM-as-judge using {judge_model}",
            False,
            None,
            str(e)[:300],
            limitations="Judge execution failed",
            judge_model=judge_model,
        )


def run_safety_evaluator(actual: str, config: dict) -> EvaluatorResult:
    """Policy-based safety checks on output text."""
    disallowed = config.get("disallowed_patterns") or []
    for pattern in disallowed:
        if re.search(pattern, actual, re.IGNORECASE):
            return EvaluatorResult(
                "safety_policy",
                "rule",
                "Configurable disallowed-content pattern matching",
                False,
                0.0,
                f"Matched disallowed pattern: {pattern}",
            )
    sensitive_patterns = config.get("sensitive_patterns") or [r"\b\d{3}-\d{2}-\d{4}\b", r"sk-[a-zA-Z0-9]+"]
    for pattern in sensitive_patterns:
        if re.search(pattern, actual):
            return EvaluatorResult(
                "sensitive_data",
                "rule",
                "Sensitive data exposure pattern check",
                False,
                0.0,
                "Potential sensitive data in output",
            )
    return EvaluatorResult(
        "safety_policy",
        "rule",
        "Configurable disallowed-content pattern matching",
        True,
        1.0,
        "No policy violations detected",
        limitations="Pattern-based safety checks cannot detect all unsafe content",
    )


def run_bias_check(cases: list[dict], config: dict) -> EvaluatorResult:
    """Group comparison bias architecture — reports differences, not 'unbiased' claims."""
    groups: dict[str, list[float]] = {}
    for case in cases:
        group = case.get("group", "default")
        score = case.get("score")
        if score is not None:
            groups.setdefault(group, []).append(float(score))

    if len(groups) < 2:
        return EvaluatorResult(
            "bias_comparison",
            "rule",
            "Group score comparison across dataset tags",
            True,
            None,
            "Insufficient groups for comparison",
            limitations="Bias testing requires multiple tagged groups in dataset metadata",
        )

    avgs = {g: sum(s) / len(s) for g, s in groups.items() if s}
    max_delta = config.get("max_score_delta", 0.2)
    if len(avgs) < 2:
        return EvaluatorResult(
            "bias_comparison", "rule", "Group score comparison", True, None, "Insufficient data"
        )

    vals = list(avgs.values())
    delta = max(vals) - min(vals)
    passed = delta <= max_delta
    return EvaluatorResult(
        "bias_comparison",
        "rule",
        "Group score comparison across dataset tags",
        passed,
        1.0 - min(delta, 1.0),
        f"Score delta across groups: {delta:.3f} (threshold {max_delta})",
        limitations=(
            "Group comparisons on limited datasets do not prove a system is unbiased. "
            "Results depend on dataset representativeness."
        ),
        evidence={"group_averages": avgs, "delta": delta},
    )


def run_hallucination_check(actual: str, reference: str, config: dict) -> EvaluatorResult:
    """Reference-based factuality check with documented limitations."""
    method = config.get("method", "reference_comparison")
    if method == "reference_comparison" and reference:
        ref_terms = set(w.lower() for w in re.findall(r"\w+", reference) if len(w) > 3)
        act_terms = set(w.lower() for w in re.findall(r"\w+", actual) if len(w) > 3)
        if not ref_terms:
            return EvaluatorResult(
                "hallucination_check",
                "rule",
                "Reference term overlap comparison",
                True,
                None,
                "No reference terms to compare",
                limitations="Cannot assess factuality without reference content",
            )
        overlap = len(ref_terms & act_terms) / len(ref_terms)
        threshold = float(config.get("min_overlap", 0.3))
        passed = overlap >= threshold
        return EvaluatorResult(
            "hallucination_check",
            "rule",
            "Reference term overlap comparison",
            passed,
            overlap,
            f"Reference overlap: {overlap:.2f} (threshold {threshold})",
            limitations=(
                "Term overlap is a heuristic, not reliable hallucination detection. "
                "Use groundedness rules or LLM judge for deeper analysis with known limitations."
            ),
            evidence={"overlap": overlap, "method": method},
        )
    return EvaluatorResult(
        "hallucination_check",
        "rule",
        method,
        True,
        None,
        "No reference provided — check skipped",
        limitations="Hallucination detection without references is unreliable",
    )
