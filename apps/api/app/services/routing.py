"""Routing orchestration.

Loads models / providers from the database, runs the engine to rank candidates
for a request, resolves each candidate to a concrete provider + credential, and
exposes the ordered target chain used to execute a request with automatic
fallback.

This service is provider-agnostic: it only sees ``Model`` / ``Provider`` rows
and the common ``AIProvider`` interface.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.models.provider import Provider, ProviderCredential
from app.models.routing import RoutingPolicy
from app.router.engine import CandidateModel, RoutingEngine
from app.services.governance.engine import GovernanceRestrictions, candidate_allowed
from app.services.cloud.region_filters import filter_targets_by_region
from app.services.cloud.regions import RegionService
from app.services.governance.pipeline import LOCAL_PROVIDER_TYPES


@dataclass
class RouteTarget:
    """One concrete candidate ready to execute: the provider + credential the
    routing engine selected, plus the resolved upstream model id to call."""

    candidate: CandidateModel
    provider: Provider
    credential: ProviderCredential | None
    resolved_model: str
    api_key: str | None = None


@dataclass
class RoutePlan:
    """The complete routing result for a request."""

    targets: list[RouteTarget]
    strategy: str
    policy_name: str | None
    requested_model: str
    required_capabilities: set[str]
    request_count: int


class RouteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = RoutingEngine()

    async def get_active_policy(self, strategy: str | None = None, policy_name: str | None = None) -> RoutingPolicy | None:
        """Resolve the routing policy to use, if any.

        Priority: explicit name or strategy override, then the configured
        default policy, then ``None`` (engine falls back to ``auto/balanced``).
        """
        if strategy:
            # A strategy override means "no named policy; use this strategy".
            return None
        if policy_name:
            result = await self.db.execute(
                select(RoutingPolicy).where(RoutingPolicy.name == policy_name)
            )
            return result.scalar_one_or_none()
        result = await self.db.execute(
            select(RoutingPolicy).where(RoutingPolicy.is_default == True)  # noqa: E712
        )
        return result.scalars().first()

    async def plan(
        self,
        requested_model: str,
        required_capabilities: set[str] | None = None,
        policy: RoutingPolicy | None = None,
        strategy: str | None = None,
        request_count: int | None = None,
        org_id: uuid.UUID | None = None,
        restrictions: GovernanceRestrictions | None = None,
        region_code: str | None = None,
        data_residency_policy: str | None = None,
    ) -> RoutePlan:
        """Build an ordered target chain for a request."""
        required = required_capabilities or {"chat"}
        strategy = strategy or (policy.strategy if policy else "auto")
        policy_config = policy.config if policy else {}

        if requested_model == "auto":
            targets = await self._plan_auto(
                required, policy, strategy, policy_config, request_count, org_id
            )
        else:
            targets = await self._plan_specific(
                requested_model, required, strategy, policy_config, org_id
            )

        if restrictions:
            filtered: list[RouteTarget] = []
            for target in targets:
                is_local = str(target.provider.type) in LOCAL_PROVIDER_TYPES
                ok, _ = candidate_allowed(
                    model_id=target.resolved_model,
                    provider_name=target.provider.name,
                    provider_type=str(target.provider.type),
                    is_local=is_local,
                    restrictions=restrictions,
                )
                if ok:
                    filtered.append(target)
            targets = filtered

        residency = data_residency_policy or (
            restrictions.data_residency_policy if restrictions else None
        )
        if residency or region_code:
            region = None
            if region_code:
                region = await RegionService(self.db).get_by_code(region_code)
            targets = filter_targets_by_region(
                targets,
                region=region,
                data_residency_policy=residency,
                region_service=RegionService(self.db),
            )

        return RoutePlan(
            targets=targets,
            strategy=strategy,
            policy_name=policy.name if policy else None,
            requested_model=requested_model,
            required_capabilities=required,
            request_count=request_count or 0,
        )

    async def _plan_auto(
        self,
        required: set[str],
        policy: RoutingPolicy | None,
        strategy: str,
        policy_config: dict,
        request_count: int | None,
        org_id: uuid.UUID | None,
    ) -> list[RouteTarget]:
        model_result = await self.db.execute(select(Model))
        models = list(model_result.scalars().all())

        provider_ids = list({str(m.provider_id) for m in models})
        if not provider_ids:
            return []
        provider_result = await self.db.execute(
            select(Provider).where(Provider.id.in_(provider_ids))
        )
        providers = list(provider_result.scalars().all())

        ordered = self.engine.ordered_candidates(
            models=models,
            providers=providers,
            strategy=strategy,
            policy_config=policy_config,
            required_capabilities=required,
            request_count=request_count,
        )
        return await self._resolve_targets(ordered)

    async def _plan_specific(
        self,
        requested_model: str,
        required: set[str],
        strategy: str,
        policy_config: dict,
        org_id: uuid.UUID | None,
    ) -> list[RouteTarget]:
        model_result = await self.db.execute(
            select(Model).where(Model.provider_model_id == requested_model, Model.is_enabled)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            return []
        if not self.engine._satisfies_capabilities(model, required):
            return []

        provider_result = await self.db.execute(
            select(Provider).where(Provider.id == model.provider_id, Provider.is_enabled)
        )
        provider = provider_result.scalar_one_or_none()
        if not provider:
            return []

        from app.models.provider import ProviderStatus

        if provider.status == ProviderStatus.OFFLINE:
            return []

        candidate = CandidateModel(model=model, provider=provider)
        return await self._resolve_targets([candidate])

    async def _resolve_targets(self, ordered: list[CandidateModel]) -> list[RouteTarget]:
        targets: list[RouteTarget] = []
        for cand in ordered:
            cred_result = await self.db.execute(
                select(ProviderCredential).where(
                    ProviderCredential.provider_id == cand.provider.id
                )
            )
            cred = cred_result.scalar_one_or_none()
            api_key = None
            if cred:
                from app.auth.encryption import decrypt_secret

                api_key = decrypt_secret(cred.encrypted_key)
            targets.append(
                RouteTarget(
                    candidate=cand,
                    provider=cand.provider,
                    credential=cred,
                    resolved_model=cand.model.provider_model_id,
                    api_key=api_key,
                )
            )
        return targets
