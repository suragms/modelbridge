"""Evaluation scorers and run execution."""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationSuite,
    PromptVersion,
)
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.gateway import execute_chat
from app.services.metrics import record_evaluation_run
from app.services.studio.workflows import substitute_prompt_variables


def score_exact_match(actual: str, expected: str) -> tuple[bool, str]:
    passed = actual.strip() == expected.strip()
    return passed, "exact match" if passed else f"expected {expected!r}, got {actual!r}"


def score_contains(actual: str, expected: str) -> tuple[bool, str]:
    passed = expected.strip().lower() in actual.strip().lower()
    return passed, "contains match" if passed else f"output missing {expected!r}"


def score_regex(actual: str, pattern: str) -> tuple[bool, str]:
    try:
        passed = bool(re.search(pattern, actual, re.IGNORECASE))
        return passed, "regex match" if passed else f"pattern {pattern!r} not found"
    except re.error as e:
        return False, f"invalid regex: {e}"


def score_json_schema(actual: str, schema: dict) -> tuple[bool, str]:
    try:
        data = json.loads(actual)
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"
    required = schema.get("required") or []
    props = schema.get("properties") or {}
    for field in required:
        if field not in data:
            return False, f"missing required field: {field}"
    for field, spec in props.items():
        if field in data and spec.get("type"):
            if not isinstance(data[field], _type_map.get(spec["type"], object)):
                return False, f"field {field} wrong type"
    return True, "schema valid"


_type_map = {"string": str, "number": (int, float), "boolean": bool, "object": dict, "array": list}


SCORERS = {
    "exact_match": score_exact_match,
    "contains": score_contains,
    "regex": score_regex,
    "json_schema": score_json_schema,
}


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_suite(
        self,
        suite: EvaluationSuite,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> EvaluationRun:
        dataset = await self.db.get(EvaluationDataset, suite.dataset_id)
        if not dataset or dataset.organization_id != org_id:
            raise ValueError("Dataset not found")

        run = EvaluationRun(
            organization_id=org_id,
            suite_id=suite.id,
            status=EvaluationRunStatus.RUNNING,
            started_by=user_id,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        prompt_content = ""
        variables_schema: list = []
        if suite.prompt_version_id:
            pv = await self.db.get(PromptVersion, suite.prompt_version_id)
            if pv:
                prompt_content = pv.content
                variables_schema = pv.variables or []

        scorers = suite.scorers or [{"type": "exact_match"}]
        primary_scorer = scorers[0].get("type", "exact_match")
        score_fn = SCORERS.get(primary_scorer, score_exact_match)

        cases = dataset.test_cases or []
        total_latency = 0.0
        total_tokens = 0
        pass_count = 0
        fail_count = 0

        for idx, case in enumerate(cases):
            input_text = case.get("input", "")
            expected = case.get("expected", "")
            case_vars = case.get("variables") or {}

            system_prompt = prompt_content
            if prompt_content and case_vars:
                system_prompt, var_errors = substitute_prompt_variables(prompt_content, case_vars)
                if var_errors:
                    fail_count += 1
                    self.db.add(
                        EvaluationResult(
                            run_id=run.id,
                            case_index=idx,
                            input_text=input_text,
                            expected=expected,
                            passed=False,
                            scorer=primary_scorer,
                            score_detail="; ".join(var_errors),
                        )
                    )
                    continue

            messages = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=input_text))

            start = time.time()
            try:
                from app.models.user import User

                user = await self.db.get(User, user_id) if user_id else None
                if not user:
                    raise ValueError("User required for evaluation runs")

                result = await execute_chat(
                    ChatCompletionRequest(
                        model=suite.model or "auto",
                        messages=messages,
                        temperature=suite.parameters.get("temperature"),
                        max_tokens=suite.parameters.get("max_tokens"),
                    ),
                    self.db,
                    user,
                    None,
                )
                latency = (time.time() - start) * 1000
                actual = ""
                if result.response.choices:
                    actual = result.response.choices[0].message.content or ""

                scorer_arg = expected
                if primary_scorer == "regex":
                    scorer_arg = scorers[0].get("pattern", expected)
                elif primary_scorer == "json_schema":
                    scorer_arg = scorers[0].get("schema", {})

                passed, detail = score_fn(actual, scorer_arg)
                if passed:
                    pass_count += 1
                else:
                    fail_count += 1

                usage = result.response.usage
                tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
                total_tokens += tokens
                total_latency += latency

                self.db.add(
                    EvaluationResult(
                        run_id=run.id,
                        case_index=idx,
                        input_text=input_text,
                        expected=expected,
                        actual_output=actual[:4000],
                        passed=passed,
                        scorer=primary_scorer,
                        score_detail=detail,
                        latency_ms=latency,
                        tokens_used=tokens,
                    )
                )
            except Exception as e:
                fail_count += 1
                self.db.add(
                    EvaluationResult(
                        run_id=run.id,
                        case_index=idx,
                        input_text=input_text,
                        expected=expected,
                        passed=False,
                        scorer=primary_scorer,
                        score_detail=str(e)[:500],
                    )
                )

        run.status = EvaluationRunStatus.COMPLETED
        run.pass_count = pass_count
        run.fail_count = fail_count
        run.total_latency_ms = total_latency
        run.total_tokens = total_tokens
        run.completed_at = datetime.now(UTC)
        record_evaluation_run(status="completed")
        await self.db.flush()
        return run

    async def get_run(self, org_id: uuid.UUID, run_id: uuid.UUID) -> EvaluationRun | None:
        run = await self.db.get(EvaluationRun, run_id)
        if not run or run.organization_id != org_id:
            return None
        return run

    async def list_results(self, run_id: uuid.UUID) -> list[EvaluationResult]:
        result = await self.db.execute(
            select(EvaluationResult).where(EvaluationResult.run_id == run_id).order_by(EvaluationResult.case_index)
        )
        return list(result.scalars().all())
