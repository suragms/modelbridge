"""AI Quality & Reliability Platform APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.quality import (
    PipelineStatus,
    QualityAlert,
    QualityAlertStatus,
    QualityEvaluationRun,
    QualityGate,
    QualityPipeline,
    QualityRegressionComparison,
    RegressionStatus,
)
from app.schemas.quality import (
    GateCreate,
    PipelineCreate,
    PipelineResponse,
    ProductionConfigUpdate,
    PromptRegressionRequest,
    QualityOverviewResponse,
    RegressionCompareRequest,
    RunResponse,
)
from app.services.quality.gates import AlertService, GateService
from app.services.quality.pipelines import PipelineService
from app.services.quality.production import ProductionQualityService
from app.services.quality.regression import RegressionService
from app.services.quality.scorecards import ScorecardService

router = APIRouter(prefix="/quality", tags=["Quality Platform"])


@router.get("/overview", response_model=QualityOverviewResponse)
async def quality_overview(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    pipelines = await db.execute(
        select(func.count()).select_from(QualityPipeline).where(
            QualityPipeline.organization_id == ctx.organization_id
        )
    )
    runs = await db.execute(
        select(func.count()).select_from(QualityEvaluationRun).where(
            QualityEvaluationRun.organization_id == ctx.organization_id
        )
    )
    alerts = await db.execute(
        select(func.count()).select_from(QualityAlert).where(
            QualityAlert.organization_id == ctx.organization_id,
            QualityAlert.status == QualityAlertStatus.OPEN,
        )
    )
    regressions = await db.execute(
        select(func.count()).select_from(QualityRegressionComparison).where(
            QualityRegressionComparison.organization_id == ctx.organization_id,
            QualityRegressionComparison.status == RegressionStatus.REGRESSION_DETECTED,
        )
    )

    quality_sc = await ScorecardService(db).compute_quality(ctx.organization_id, "7d")
    reliability_sc = await ScorecardService(db).compute_reliability(ctx.organization_id, "7d")
    await db.commit()

    recent_regs = await RegressionService(db).list_comparisons(ctx.organization_id, limit=5)
    recent_alerts = await AlertService(db).list_alerts(ctx.organization_id, limit=5)

    return QualityOverviewResponse(
        pipelines=pipelines.scalar() or 0,
        recent_runs=runs.scalar() or 0,
        open_alerts=alerts.scalar() or 0,
        regressions_detected=regressions.scalar() or 0,
        overall_quality=quality_sc.overall_score,
        reliability_score=reliability_sc.overall_score,
        confidence=quality_sc.confidence,
        recent_regressions=[
            {
                "id": str(r.id),
                "type": r.comparison_type,
                "status": r.status,
                "baseline": r.baseline_label,
                "candidate": r.candidate_label,
                "differences": r.differences,
            }
            for r in recent_regs
        ],
        recent_alerts=[
            {"id": str(a.id), "type": a.alert_type, "title": a.title, "status": a.status}
            for a in recent_alerts
        ],
    )


@router.get("/pipelines", response_model=list[PipelineResponse])
async def list_pipelines(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await PipelineService(db).list_pipelines(ctx.organization_id)
    return [
        PipelineResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            dataset_id=p.dataset_id,
            schedule=p.schedule,
            created_at=p.created_at,
        )
        for p in items
    ]


@router.post("/pipelines", status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    payload: PipelineCreate,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        pipeline, version = await PipelineService(db).create(
            org_id=ctx.organization_id,
            name=payload.name,
            description=payload.description,
            dataset_id=payload.dataset_id,
            evaluators=payload.evaluators,
            thresholds=payload.thresholds,
            model=payload.model,
            parameters=payload.parameters,
            prompt_version_id=payload.prompt_version_id,
            user_id=ctx.user.id,
            schedule=payload.schedule,
            trigger_on=payload.trigger_on,
        )
        pipeline.status = PipelineStatus.ACTIVE
        await db.commit()
        return {"id": str(pipeline.id), "version_id": str(version.id), "version": version.version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/pipelines/{pipeline_id}/run", response_model=RunResponse)
async def run_pipeline(
    pipeline_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await PipelineService(db).get_pipeline(ctx.organization_id, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    try:
        run = await PipelineService(db).run(
            pipeline, org_id=ctx.organization_id, user_id=ctx.user.id, trigger="manual"
        )
        await db.commit()
        return RunResponse(
            id=run.id,
            pipeline_id=run.pipeline_id,
            status=run.status,
            pass_count=run.pass_count,
            fail_count=run.fail_count,
            pass_rate=run.pass_rate,
            total_latency_ms=run.total_latency_ms,
            total_tokens=run.total_tokens,
            total_cost=run.total_cost,
            trigger=run.trigger,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(QualityEvaluationRun, run_id)
    if not run or run.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(
        id=run.id,
        pipeline_id=run.pipeline_id,
        status=run.status,
        pass_count=run.pass_count,
        fail_count=run.fail_count,
        pass_rate=run.pass_rate,
        total_latency_ms=run.total_latency_ms,
        total_tokens=run.total_tokens,
        total_cost=run.total_cost,
        trigger=run.trigger,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/regressions")
async def list_regressions(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await RegressionService(db).list_comparisons(ctx.organization_id)
    return [
        {
            "id": str(r.id),
            "comparison_type": r.comparison_type,
            "baseline": r.baseline_label,
            "candidate": r.candidate_label,
            "status": r.status,
            "metrics": r.metrics,
            "differences": r.differences,
            "thresholds": r.thresholds,
            "created_at": r.created_at.isoformat(),
        }
        for r in items
    ]


@router.post("/regressions/compare", status_code=status.HTTP_201_CREATED)
async def compare_regressions(
    payload: RegressionCompareRequest,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        comparison = await RegressionService(db).compare_runs(
            org_id=ctx.organization_id,
            comparison_type=payload.comparison_type,
            baseline_label=payload.baseline_label,
            candidate_label=payload.candidate_label,
            baseline_run_id=payload.baseline_run_id,
            candidate_run_id=payload.candidate_run_id,
            thresholds=payload.thresholds,
            user_id=ctx.user.id,
        )
        await db.commit()
        return {"id": str(comparison.id), "status": comparison.status, "differences": comparison.differences}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/regressions/prompt", status_code=status.HTTP_201_CREATED)
async def prompt_regression(
    payload: PromptRegressionRequest,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = PipelineService(db)
        comparison = await RegressionService(db).compare_prompt_versions(
            org_id=ctx.organization_id,
            pipeline_id=payload.pipeline_id,
            baseline_prompt_version_id=payload.baseline_prompt_version_id,
            candidate_prompt_version_id=payload.candidate_prompt_version_id,
            user_id=ctx.user.id,
            pipeline_service=svc,
        )
        await db.commit()
        return {"id": str(comparison.id), "status": comparison.status, "differences": comparison.differences}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/scorecards")
async def list_scorecards(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await ScorecardService(db).list_scorecards(ctx.organization_id)
    return [
        {
            "id": str(s.id),
            "type": s.scorecard_type,
            "time_range": s.time_range,
            "overall_score": s.overall_score,
            "dimensions": s.dimensions,
            "formula": s.formula,
            "limitations": s.limitations,
            "confidence": s.confidence,
            "computed_at": s.computed_at.isoformat(),
        }
        for s in items
    ]


@router.post("/scorecards/reliability")
async def compute_reliability_scorecard(
    time_range: str = "7d",
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    sc = await ScorecardService(db).compute_reliability(ctx.organization_id, time_range)
    await db.commit()
    return {
        "id": str(sc.id),
        "overall_score": sc.overall_score,
        "dimensions": sc.dimensions,
        "formula": sc.formula,
        "limitations": sc.limitations,
        "confidence": sc.confidence,
    }


@router.post("/scorecards/quality")
async def compute_quality_scorecard(
    time_range: str = "7d",
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    sc = await ScorecardService(db).compute_quality(ctx.organization_id, time_range)
    await db.commit()
    return {
        "id": str(sc.id),
        "overall_score": sc.overall_score,
        "dimensions": sc.dimensions,
        "formula": sc.formula,
        "limitations": sc.limitations,
        "confidence": sc.confidence,
    }


@router.get("/gates")
async def list_gates(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    gates = await GateService(db).list_gates(ctx.organization_id)
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "pipeline_id": str(g.pipeline_id),
            "min_pass_rate": g.min_pass_rate,
            "block_deployment": g.block_deployment,
        }
        for g in gates
    ]


@router.post("/gates", status_code=status.HTTP_201_CREATED)
async def create_gate(
    payload: GateCreate,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    gate = await GateService(db).create(
        org_id=ctx.organization_id,
        name=payload.name,
        pipeline_id=payload.pipeline_id,
        min_pass_rate=payload.min_pass_rate,
        min_safety_score=payload.min_safety_score,
        max_regression_delta=payload.max_regression_delta,
        block_deployment=payload.block_deployment,
    )
    await db.commit()
    return {"id": str(gate.id)}


@router.get("/alerts")
async def list_alerts(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    alerts = await AlertService(db).list_alerts(ctx.organization_id)
    return [
        {
            "id": str(a.id),
            "type": a.alert_type,
            "title": a.title,
            "status": a.status,
            "evidence": a.evidence,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.get("/incidents")
async def list_incidents(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    incidents = await AlertService(db).list_incidents(ctx.organization_id)
    return [
        {
            "id": str(i.id),
            "title": i.title,
            "status": i.status,
            "affected_version": i.affected_version,
            "evidence": i.evidence,
            "detected_at": i.detected_at.isoformat(),
        }
        for i in incidents
    ]


@router.get("/production")
async def production_status(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    config = await ProductionQualityService(db).get_or_create_config(ctx.organization_id)
    samples = await ProductionQualityService(db).list_samples(ctx.organization_id, limit=10)
    return {
        "config": {
            "enabled": config.enabled,
            "sampling_rate": config.sampling_rate,
            "retention_days": config.retention_days,
            "redaction_policy": config.redaction_policy,
        },
        "recent_samples": [
            {
                "request_id": s.request_id,
                "model": s.model,
                "status": s.status,
                "quality_signals": s.quality_signals,
                "evaluated_at": s.evaluated_at.isoformat(),
            }
            for s in samples
        ],
    }


@router.patch("/production")
async def update_production_config(
    payload: ProductionConfigUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    config = await ProductionQualityService(db).update_config(
        ctx.organization_id,
        enabled=payload.enabled,
        sampling_rate=payload.sampling_rate,
        sampling_rules=payload.sampling_rules,
        redaction_policy=payload.redaction_policy,
        retention_days=payload.retention_days,
        pipeline_id=payload.pipeline_id,
    )
    await db.commit()
    return {"enabled": config.enabled, "sampling_rate": config.sampling_rate}


@router.post("/production/sample")
async def trigger_production_sample(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    samples = await ProductionQualityService(db).sample_requests(ctx.organization_id)
    await db.commit()
    return {"sampled": len(samples)}


@router.get("/models/comparison")
async def model_quality_comparison(
    ctx: OrgContext = Depends(require_permission(Permission.QUALITY_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QualityEvaluationRun)
        .where(QualityEvaluationRun.organization_id == ctx.organization_id)
        .order_by(QualityEvaluationRun.completed_at.desc())
        .limit(50)
    )
    runs = list(result.scalars().all())
    by_model: dict[str, dict] = {}
    for run in runs:
        model = (run.evidence or {}).get("model", "unknown")
        entry = by_model.setdefault(model, {"runs": 0, "pass_rates": [], "latencies": [], "failures": 0})
        entry["runs"] += 1
        if run.pass_rate is not None:
            entry["pass_rates"].append(run.pass_rate)
        entry["latencies"].append(run.total_latency_ms)
        entry["failures"] += run.fail_count

    return [
        {
            "model": model,
            "runs": data["runs"],
            "avg_pass_rate": sum(data["pass_rates"]) / len(data["pass_rates"]) if data["pass_rates"] else None,
            "avg_latency_ms": sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else None,
            "total_failures": data["failures"],
            "methodology": "Aggregated from completed quality evaluation runs",
        }
        for model, data in by_model.items()
    ]
