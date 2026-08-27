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
from app.router.engine import RoutingEngine
from app.schemas.routing import (
    RouteCandidate,
    RoutingPolicyCreate,
    RoutingPolicyResponse,
    RoutingPolicyUpdate,
    RoutingTestRequest,
    RoutingTestResponse,
)
from app.services.routing import RouteService

router = APIRouter(prefix="/routing", tags=["Routing"])


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
    # If this is default, unset any existing default
    if payload.is_default:
        await db.execute(
            select(RoutingPolicy).where(RoutingPolicy.is_default == True)  # noqa: E712
        )

    policy = RoutingPolicy(
        name=payload.name,
        description=payload.description,
        strategy=payload.strategy,
        config=payload.config or {},
        is_default=payload.is_default,
    )
    db.add(policy)
    await db.flush()
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
            # Unset any existing default
            await db.execute(
                select(RoutingPolicy).where(
                    RoutingPolicy.is_default == True, RoutingPolicy.id != policy_id  # noqa: E712
                )
            )
        policy.is_default = payload.is_default

    await db.flush()
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
    if payload.requested_model != "auto":
        required.add("chat")  # specific model must support chat

    plan = await route_service.plan(
        requested_model=payload.requested_model,
        required_capabilities=required,
        policy=policy,
        strategy=payload.strategy,
        org_id=user.organization_id,
    )

    # Build candidate list (all candidates before filtering)
    model_result = await db.execute(select(Model))
    all_models = list(model_result.scalars().all())

    provider_ids = list({str(m.provider_id) for m in all_models})
    provider_result = await db.execute(select(Provider).where(Provider.id.in_(provider_ids)))
    all_providers = list(provider_result.scalars().all())

    engine = RoutingEngine()
    all_candidates = engine.build_candidates(all_models, all_providers, required)
    all_candidates = engine.ordered_candidates(
        all_models,
        all_providers,
        payload.strategy or (policy.strategy if policy else "auto"),
        policy.config if policy else {},
        required,
    )

    # Filtered = those that are actually eligible (not disabled/offline)
    filtered = engine.build_candidates(all_models, all_providers, required)
    filtered = engine.ordered_candidates(
        all_models,
        all_providers,
        payload.strategy or (policy.strategy if policy else "auto"),
        policy.config if policy else {},
        required,
    )

    selected = plan.targets[0] if plan.targets else None
    reason = f"Selected via {plan.strategy} strategy" if selected else "No eligible models found"

    # Build fallback order from the plan
    fallback_order = [str(t.candidate.model.id) for t in plan.targets[1:]]

    return RoutingTestResponse(
        candidates=[
            RouteCandidate(
                model_id=c.model.id,
                model_name=c.model.display_name,
                provider_name=c.provider.name,
                provider_type=c.provider.type.value,
                score=c.score,
                latency_ms=c.latency_ms,
                cost_per_1k=c.cost_per_1k,
                is_local=c.provider.type.value in {"ollama", "lmstudio"},
            )
            for c in all_candidates
        ],
        filtered=[
            RouteCandidate(
                model_id=c.model.id,
                model_name=c.model.display_name,
                provider_name=c.provider.name,
                provider_type=c.provider.type.value,
                score=c.score,
                latency_ms=c.latency_ms,
                cost_per_1k=c.cost_per_1k,
                is_local=c.provider.type.value in {"ollama", "lmstudio"},
            )
            for c in filtered
        ],
        selected=RouteCandidate(
            model_id=selected.candidate.model.id,
            model_name=selected.candidate.model.display_name,
            provider_name=selected.provider.name,
            provider_type=selected.provider.type.value,
            score=selected.candidate.score,
            latency_ms=selected.candidate.latency_ms,
            cost_per_1k=selected.candidate.cost_per_1k,
            is_local=selected.provider.type.value in {"ollama", "lmstudio"},
        )
        if selected
        else None,
        strategy=plan.strategy,
        reason=reason,
        fallback_order=fallback_order,
    )