"""Intelligence layer APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.schemas.intelligence import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    RecommendationActionRequest,
    RecommendationResponse,
)
from app.services.enterprise.activity import record_activity
from app.services.intelligence.anomalies import AnomalyService
from app.services.intelligence.assistant import OperationsAssistant
from app.services.intelligence.capacity import CapacityService
from app.services.intelligence.cost import CostIntelligenceService
from app.services.intelligence.engine import IntelligenceEngine
from app.services.intelligence.forecasting import ForecastingService
from app.services.intelligence.incidents import IncidentIntelligenceService
from app.services.intelligence.providers import ProviderIntelligenceService
from app.services.intelligence.recommendations import RecommendationService

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])
assistant_router = APIRouter(prefix="/operations-assistant", tags=["Operations Assistant"])


@router.get("/overview")
async def intelligence_overview(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    data = await IntelligenceEngine(db).overview(ctx.organization_id)
    await db.commit()
    return data


@router.get("/providers")
async def provider_intelligence(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
    days: int = 7,
):
    data = await ProviderIntelligenceService(db).analyze(ctx.organization_id, days=days)
    await db.commit()
    return data


@router.get("/costs")
async def cost_intelligence(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
    days: int = 30,
):
    data = await CostIntelligenceService(db).analyze(ctx.organization_id, days=days)
    await db.commit()
    return data


@router.get("/capacity")
async def capacity_intelligence(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    data = await CapacityService(db).analyze(ctx.organization_id)
    await db.commit()
    return data


@router.get("/anomalies")
async def list_anomalies(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
):
    return await AnomalyService(db).list_anomalies(ctx.organization_id, status=status)


@router.post("/anomalies/detect")
async def detect_anomalies(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    data = await AnomalyService(db).detect(ctx.organization_id)
    await db.commit()
    return data


@router.get("/forecasts/requests")
async def forecast_requests(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    data = await ForecastingService(db).forecast_requests(ctx.organization_id)
    await db.commit()
    return data


@router.get("/forecasts/costs")
async def forecast_costs(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    data = await ForecastingService(db).forecast_cost(ctx.organization_id)
    await db.commit()
    return data


@router.get("/recommendations", response_model=list[RecommendationResponse])
async def list_recommendations(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    category: str | None = None,
):
    recs = await RecommendationService(db).list_recommendations(
        ctx.organization_id, status=status, category=category
    )
    return recs


@router.post("/recommendations/{rec_id}/acknowledge", response_model=RecommendationResponse)
async def acknowledge_recommendation(
    rec_id: uuid.UUID,
    payload: RecommendationActionRequest,
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = RecommendationService(db)
    rec = await svc.get(ctx.organization_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec = await svc.transition(rec, "acknowledge", actor_id=ctx.user.id, notes=payload.notes)
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="intelligence.recommendation.acknowledged",
        resource_type="recommendation",
        resource_id=str(rec_id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    return rec


@router.post("/recommendations/{rec_id}/approve", response_model=RecommendationResponse)
async def approve_recommendation(
    rec_id: uuid.UUID,
    payload: RecommendationActionRequest,
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_APPROVE)),
    db: AsyncSession = Depends(get_db),
):
    svc = RecommendationService(db)
    rec = await svc.get(ctx.organization_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    try:
        rec = await svc.transition(rec, "approve", actor_id=ctx.user.id, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="intelligence.recommendation.approved",
        resource_type="recommendation",
        resource_id=str(rec_id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    return rec


@router.post("/recommendations/{rec_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_recommendation(
    rec_id: uuid.UUID,
    payload: RecommendationActionRequest,
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = RecommendationService(db)
    rec = await svc.get(ctx.organization_id, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec = await svc.transition(rec, "dismiss", actor_id=ctx.user.id, notes=payload.notes)
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="intelligence.recommendation.dismissed",
        resource_type="recommendation",
        resource_id=str(rec_id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    return rec


@router.post("/analyze")
async def run_analysis(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
    job_type: str = "full",
):
    result = await IntelligenceEngine(db).run_analysis(ctx.organization_id, job_type=job_type)
    await db.commit()
    return result


@router.get("/jobs")
async def job_health(
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await IntelligenceEngine(db).job_health(ctx.organization_id)


@router.get("/incidents/{incident_id}/analysis")
async def incident_analysis(
    incident_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await IncidentIntelligenceService(db).analyze_incident(ctx.organization_id, incident_id)


@assistant_router.post("/query", response_model=AssistantQueryResponse)
async def assistant_query(
    payload: AssistantQueryRequest,
    ctx: OrgContext = Depends(require_permission(Permission.INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await OperationsAssistant(db).query(ctx.organization_id, payload.question)
    return result
