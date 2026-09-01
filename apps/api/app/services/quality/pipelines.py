"""Quality evaluation pipeline orchestration."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    PipelineStatus,
    QualityEvaluationRun,
    QualityPipeline,
    QualityPipelineVersion,
    QualityRunStatus,
)
from app.models.studio import EvaluationDataset, PromptVersion
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.gateway import execute_chat
from app.services.metrics import record_quality_evaluation
from app.services.platform.events import EventBus
from app.services.quality.evaluators import run_evaluator
from app.services.studio.workflows import substitute_prompt_variables


class PipelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        description: str | None,
        dataset_id: uuid.UUID,
        evaluators: list[dict],
        thresholds: dict | None,
        model: str,
        parameters: dict | None,
        prompt_version_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        schedule: str | None = None,
        trigger_on: list[str] | None = None,
    ) -> tuple[QualityPipeline, QualityPipelineVersion]:
        dataset = await self.db.get(EvaluationDataset, dataset_id)
        if not dataset or dataset.organization_id != org_id:
            raise ValueError("Dataset not found")

        pipeline = QualityPipeline(
            organization_id=org_id,
            name=name,
            description=description,
            input_source="dataset",
            dataset_id=dataset_id,
            schedule=schedule,
            trigger_on=trigger_on or [],
            status=PipelineStatus.DRAFT,
            created_by=user_id,
        )
        self.db.add(pipeline)
        await self.db.flush()

        version = QualityPipelineVersion(
            pipeline_id=pipeline.id,
            organization_id=org_id,
            version=1,
            evaluators=evaluators,
            thresholds=thresholds or {"min_pass_rate": 0.9},
            prompt_version_id=prompt_version_id,
            model=model,
            parameters=parameters or {},
            change_summary="Initial version",
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()
        pipeline.current_version_id = version.id
        await self.db.flush()
        return pipeline, version

    async def get_pipeline(self, org_id: uuid.UUID, pipeline_id: uuid.UUID) -> QualityPipeline | None:
        p = await self.db.get(QualityPipeline, pipeline_id)
        if not p or p.organization_id != org_id:
            return None
        return p

    async def list_pipelines(self, org_id: uuid.UUID) -> list[QualityPipeline]:
        result = await self.db.execute(
            select(QualityPipeline)
            .where(QualityPipeline.organization_id == org_id)
            .order_by(QualityPipeline.updated_at.desc())
        )
        return list(result.scalars().all())

    async def run(
        self,
        pipeline: QualityPipeline,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
        trigger: str = "manual",
    ) -> QualityEvaluationRun:
        if not pipeline.current_version_id:
            raise ValueError("Pipeline has no version")

        version = await self.db.get(QualityPipelineVersion, pipeline.current_version_id)
        if not version or version.organization_id != org_id:
            raise ValueError("Pipeline version not found")

        dataset = await self.db.get(EvaluationDataset, pipeline.dataset_id)
        if not dataset or dataset.organization_id != org_id:
            raise ValueError("Dataset not found")

        user = await self.db.get(User, user_id) if user_id else None
        if not user:
            raise ValueError("User required for evaluation runs")

        run = QualityEvaluationRun(
            organization_id=org_id,
            pipeline_id=pipeline.id,
            pipeline_version_id=version.id,
            pipeline_version=version.version,
            status=QualityRunStatus.RUNNING,
            trigger=trigger,
            started_by=user_id,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        prompt_content = ""
        if version.prompt_version_id:
            pv = await self.db.get(PromptVersion, version.prompt_version_id)
            if pv:
                prompt_content = pv.content

        cases = dataset.test_cases or []
        evaluators = version.evaluators or [{"type": "rule", "name": "exact_match", "config": {"rule": "exact_match"}}]
        pass_count = 0
        fail_count = 0
        total_latency = 0.0
        total_tokens = 0
        total_cost = 0.0
        case_results: list[dict] = []

        for idx, case in enumerate(cases):
            input_text = case.get("input", "")
            expected = case.get("expected", "")
            case_vars = case.get("variables") or {}
            metadata = case.get("metadata") or {}

            system_prompt = prompt_content
            if prompt_content and case_vars:
                system_prompt, var_errors = substitute_prompt_variables(prompt_content, case_vars)
                if var_errors:
                    fail_count += 1
                    case_results.append({"case_index": idx, "passed": False, "errors": var_errors})
                    continue

            messages = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=input_text))

            start = time.time()
            try:
                result = await execute_chat(
                    ChatCompletionRequest(
                        model=version.model or "auto",
                        messages=messages,
                        temperature=version.parameters.get("temperature"),
                        max_tokens=version.parameters.get("max_tokens"),
                    ),
                    self.db,
                    user,
                    None,
                )
                latency = (time.time() - start) * 1000
                actual = ""
                if result.response.choices:
                    actual = result.response.choices[0].message.content or ""

                usage = result.response.usage
                tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
                total_latency += latency
                total_tokens += tokens
                if result.estimated_total_cost:
                    total_cost += result.estimated_total_cost

                eval_results = []
                case_passed = True
                for ev in evaluators:
                    ev_result = await run_evaluator(
                        ev, actual=actual, expected=expected, input_text=input_text, db=self.db, user=user
                    )
                    eval_results.append({
                        "name": ev_result.evaluator_name,
                        "type": ev_result.evaluator_type,
                        "methodology": ev_result.methodology,
                        "passed": ev_result.passed,
                        "score": ev_result.score,
                        "detail": ev_result.detail,
                        "limitations": ev_result.limitations,
                        "judge_model": ev_result.judge_model,
                    })
                    if not ev_result.passed:
                        case_passed = False

                if case_passed:
                    pass_count += 1
                else:
                    fail_count += 1

                case_results.append({
                    "case_index": idx,
                    "passed": case_passed,
                    "latency_ms": latency,
                    "evaluators": eval_results,
                    "metadata": metadata,
                })
            except Exception as e:
                fail_count += 1
                case_results.append({"case_index": idx, "passed": False, "error": str(e)[:300]})

        total = pass_count + fail_count
        pass_rate = pass_count / total if total else None

        run.status = QualityRunStatus.COMPLETED
        run.pass_count = pass_count
        run.fail_count = fail_count
        run.pass_rate = pass_rate
        run.total_latency_ms = total_latency
        run.total_tokens = total_tokens
        run.total_cost = total_cost if total_cost else None
        run.evaluator_results = case_results
        run.evidence = {
            "evaluator_count": len(evaluators),
            "dataset_id": str(dataset.id),
            "model": version.model,
        }
        run.completed_at = datetime.now(UTC)
        record_quality_evaluation(status="completed")

        min_pass = float((version.thresholds or {}).get("min_pass_rate", 0.9))
        event_type = "evaluation.completed" if (pass_rate or 0) >= min_pass else "evaluation.failed"
        await EventBus(self.db).emit(
            organization_id=org_id,
            event_type=event_type,
            data={
                "execution_id": str(run.id),
                "status": run.status,
                "latency_ms": int(total_latency),
            },
            source="quality",
        )

        if pass_rate is not None and pass_rate < min_pass:
            from app.services.quality.alerts import AlertService

            await AlertService(self.db).create_threshold_violation(
                org_id=org_id,
                run_id=run.id,
                pass_rate=pass_rate,
                threshold=min_pass,
            )

        await self.db.flush()
        return run

    async def add_version(
        self,
        pipeline: QualityPipeline,
        *,
        evaluators: list[dict],
        thresholds: dict | None,
        change_summary: str | None,
        user_id: uuid.UUID | None,
    ) -> QualityPipelineVersion:
        result = await self.db.execute(
            select(func.max(QualityPipelineVersion.version)).where(
                QualityPipelineVersion.pipeline_id == pipeline.id
            )
        )
        next_ver = (result.scalar() or 0) + 1
        current = await self.db.get(QualityPipelineVersion, pipeline.current_version_id) if pipeline.current_version_id else None

        version = QualityPipelineVersion(
            pipeline_id=pipeline.id,
            organization_id=pipeline.organization_id,
            version=next_ver,
            evaluators=evaluators,
            thresholds=thresholds or (current.thresholds if current else {}),
            prompt_version_id=current.prompt_version_id if current else None,
            model=current.model if current else "auto",
            parameters=current.parameters if current else {},
            change_summary=change_summary or f"Version {next_ver}",
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()
        pipeline.current_version_id = version.id
        pipeline.updated_at = datetime.now(UTC)
        await self.db.flush()
        return version
