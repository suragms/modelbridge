from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.model import Model
from app.models.provider import Provider
from app.models.routing import RoutingPolicy
from app.models.user import User
from app.router.engine import CandidateModel, RoutingEngine
from app.schemas.routing import (
    RouteCandidate,
    RoutingDebugEntry,
    RoutingPolicyCreate,
    RoutingPolicyResponse,
    RoutingPolicyUpdate,
    RoutingTestRequest,
    RoutingTestResponse,
)
from app.services.audit import (
    AUDIT_ROUTING_POLICY_CREATED,
    AUDIT_ROUTING_POLICY_UPDATED,
    AuditService,
)
from app.services.routing import RouteService

router = APIRouter(prefix="/routing", tags=["Routing"])


async def _clear_default(db: AsyncSession, exclude_id: uuid.UUID | None = None) -> None:
    """Unset ``is_default`` on any current default policy, optionally excluding one id."""
    query = select(RoutingPolicy).where(RoutingPolicy.is_default == True)  # noqa: E712
    if exclude_id is not None:
        query = query.where(RoutingPolicy.id != exclude_id)
    result = await db.execute(query)
    for policy in result.scalars().all():
        policy.is_default = False


@router.get("/policies", response_model=list[RoutingPolicyResponse])
async def list_routing_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingPolicy).where(RoutingPolicy.is_default == False).order_by(RoutingPolicy.name)  # noqa: E712
    )
    policies = list(result.scalars().all())
    # Add default policy first if exists
    default_result = await db.execute(
        select(RoutingPolicy).where(RoutingPolicy.is_default == True)  # noqa: E712
    )
    default_policy = default_result.scalars().first()
    if default_policy:
        policies = [default_policy] + policies
    return [RoutingPolicyResponse.model_validate(p) for p in policies]


@router.post("/policies", response_model=RoutingPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_policy(
    payload: RoutingPolicyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # If this is default, unset any existing default policy
    if payload.is_default:
        await _clear_default(db)

    policy = RoutingPolicy(
        name=payload.name,
        description=payload.description,
        strategy=payload.strategy,
        config=payload.config or {},
        is_default=payload.is_default,
    )
    db.add(policy)
    await db.flush()
    audit = AuditService(db)
    await audit.log(
        AUDIT_ROUTING_POLICY_CREATED, "routing_policy", str(policy.id),
        actor=user, metadata={"name": policy.name, "strategy": policy.strategy},
    )
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def get_routing_policy(
    policy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingPolicy).where(RoutingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")
    return RoutingPolicyResponse.model_validate(policy)


@router.patch("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def update_routing_policy(
    policy_id: uuid.UUID,
    payload: RoutingPolicyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingPolicy).where(RoutingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")

    if payload.name is not None:
        policy.name = payload.name
    if payload.description is not None:
        policy.description = payload.description
    if payload.strategy is not None:
        policy.strategy = payload.strategy
    if payload.config is not None:
        policy.config = payload.config
    if payload.is_default is not None:
        if payload.is_default:
            # Unset any other existing default policy.
            await _clear_default(db, exclude_id=policy_id)
        policy.is_default = payload.is_default
        if not payload.is_default:
            # Never leave the system without at least one default when removing it.
            count_result = await db.execute(
                select(RoutingPolicy.id).where(
                    RoutingPolicy.is_default == True  # noqa: E712
                )
            )
            if not count_result.first():
                policy.is_default = True

    await db.flush()
    audit = AuditService(db)
    await audit.log(
        AUDIT_ROUTING_POLICY_UPDATED, "routing_policy", str(policy.id),
        actor=user, metadata={"name": policy.name, "strategy": policy.strategy},
    )
    return RoutingPolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_policy(
    policy_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutingPolicy).where(RoutingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing policy not found")

    if policy.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default policy")

    await db.delete(policy)
    await db.flush()


@router.post("/test", response_model=RoutingTestResponse)
async def test_routing(
    payload: RoutingTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test the routing engine without executing a request.

    Returns the full candidate list, the filtered/eligible candidates, the
    selected model/provider according to the strategy, and the fallback chain.
    """
    route_service = RouteService(db)

    # Resolve policy if requested
    policy = None
    if payload.policy_name:
        result = await db.execute(
            select(RoutingPolicy).where(RoutingPolicy.name == payload.policy_name)
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy '{payload.policy_name}' not found")

    required = set(payload.required_capabilities) if payload.required_capabilities else {"chat"}
    if payload.requested_model != "auto" and "embeddings" not in required:
        required.add("chat")

    plan = await route_service.plan(
        requested_model=payload.requested_model,
        required_capabilities=required,
        policy=policy,
        strategy=payload.strategy,
        org_id=user.organization_id,
    )

    strategy = payload.strategy or (policy.strategy if policy else "auto")
    policy_config = policy.config if policy else {}

    # All models in the registry (informational), ranked by the strategy.
    model_result = await db.execute(select(Model))
    all_models = list(model_result.scalars().all())

    provider_ids = list({str(m.provider_id) for m in all_models})
    provider_map = {}
    if provider_ids:
        provider_result = await db.execute(select(Provider).where(Provider.id.in_(provider_ids)))
        provider_map = {str(p.id): p for p in provider_result.scalars().all()}

    engine = RoutingEngine()
    ordered = engine.ordered_candidates(
        all_models,
        list(provider_map.values()),
        strategy,
        policy_config,
        required,
    )

    # "candidates" = every model ranked; "filtered" = those the engine would
    # actually use (eligible: enabled, healthy provider, satisfies capabilities).
    eligible_ids = {str(c.model.id) for c in ordered}
    remaining = [
        CandidateModel(model=m, provider=provider_map[str(m.provider_id)])
        for m in all_models
        if str(m.id) not in eligible_ids and str(m.provider_id) in provider_map
    ]
    # Rank remaining by strategy too so the view stays consistent.
    remaining_ranked = engine.ordered_candidates(
        [r.model for r in remaining],
        list({r.provider for r in remaining}),
        strategy,
        policy_config,
        set(),
    )
    all_candidates = ordered + remaining_ranked

    selected = plan.targets[0] if plan.targets else None
    reason = f"Selected via {plan.strategy} strategy" if selected else "No eligible models found"

    # Build fallback order from the plan
    fallback_order = [str(t.candidate.model.id) for t in plan.targets[1:]]

    debug_entries: list[RoutingDebugEntry] = []
    for m in all_models:
        provider = provider_map.get(str(m.provider_id))
        reason = RoutingEngine.explain_filter(m, provider, required)
        debug_entries.append(RoutingDebugEntry(
            model_id=m.id,
            model_name=m.display_name,
            provider_name=provider.name if provider else "unknown",
            eligible=reason is None,
            filter_reason=reason,
        ))

    def _candidate(c, eligible: bool) -> RouteCandidate:
        reason = RoutingEngine.explain_filter(c.model, c.provider, required)
        return RouteCandidate(
            model_id=c.model.id,
            model_name=c.model.display_name,
            provider_name=c.provider.name,
            provider_type=c.provider.type.value,
            score=c.score,
            latency_ms=c.latency_ms,
            cost_per_1k=c.cost_per_1k,
            is_local=c.provider.type.value in {"ollama", "lmstudio"},
            eligible=eligible,
            filter_reason=reason,
        )

    return RoutingTestResponse(
        candidates=[_candidate(c, str(c.model.id) in eligible_ids) for c in all_candidates],
        filtered=[_candidate(c, True) for c in ordered],
        debug=debug_entries,
        requested_capabilities=sorted(required),
        selected=_candidate(selected.candidate, True) if selected else None,
        strategy=plan.strategy,
        reason=reason,
        fallback_order=fallback_order,
    )
