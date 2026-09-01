"""FinOps cost calculation engine with pricing version tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import CostType, FinopsProviderPricing
from app.models.request_log import CostRecord, PRICING_SOURCE_UNKNOWN
from app.services.pricing import PricingInfo, PricingRegistry


def classify_cost_type(*, is_estimated: bool, pricing_source: str) -> str:
    if pricing_source == PRICING_SOURCE_UNKNOWN or pricing_source.lower() == "unknown":
        return CostType.UNKNOWN
    if pricing_source in ("manual", "configured"):
        return CostType.CONFIGURED if not is_estimated else CostType.ESTIMATED
    if is_estimated:
        return CostType.ESTIMATED
    return CostType.ACTUAL


class CostEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = PricingRegistry(db)

    async def get_pricing_at(
        self,
        provider: str,
        model: str,
        *,
        org_id: uuid.UUID | None = None,
        as_of: datetime | None = None,
    ) -> tuple[PricingInfo, int | None]:
        as_of = as_of or datetime.now(UTC)
        q = select(FinopsProviderPricing).where(
            FinopsProviderPricing.provider == provider,
            FinopsProviderPricing.model == model,
            FinopsProviderPricing.effective_from <= as_of,
        )
        if org_id:
            q = q.where(
                (FinopsProviderPricing.organization_id == org_id)
                | (FinopsProviderPricing.organization_id.is_(None))
            )
        q = q.order_by(FinopsProviderPricing.effective_from.desc()).limit(1)
        result = await self.db.execute(q)
        versioned = result.scalar_one_or_none()
        if versioned and (versioned.effective_to is None or versioned.effective_to > as_of):
            info = PricingInfo(
                input_price_per_million=versioned.input_price_per_million,
                output_price_per_million=versioned.output_price_per_million,
                currency=versioned.currency,
                pricing_source="configured",
                is_known=True,
            )
            return info, versioned.version

        info = await self.registry.get_pricing(model)
        return info, None

    def calculate(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        pricing: PricingInfo,
        cached_tokens: int = 0,
    ) -> dict:
        input_cost, output_cost, total_cost, is_estimated = PricingRegistry.calculate_cost(
            input_tokens, output_tokens, pricing
        )
        cost_type = classify_cost_type(is_estimated=is_estimated, pricing_source=pricing.pricing_source)
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "cost_type": cost_type,
            "currency": pricing.currency,
            "pricing_source": pricing.pricing_source,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
        }

    async def create_pricing_version(
        self,
        *,
        org_id: uuid.UUID | None,
        provider: str,
        model: str,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str,
        user_id: uuid.UUID | None,
    ) -> FinopsProviderPricing:
        result = await self.db.execute(
            select(func.max(FinopsProviderPricing.version)).where(
                FinopsProviderPricing.provider == provider,
                FinopsProviderPricing.model == model,
                FinopsProviderPricing.organization_id == org_id if org_id else FinopsProviderPricing.organization_id.is_(None),
            )
        )
        next_ver = (result.scalar() or 0) + 1
        now = datetime.now(UTC)

        active = await self.db.execute(
            select(FinopsProviderPricing).where(
                FinopsProviderPricing.provider == provider,
                FinopsProviderPricing.model == model,
                FinopsProviderPricing.effective_to.is_(None),
                FinopsProviderPricing.organization_id == org_id if org_id else FinopsProviderPricing.organization_id.is_(None),
            )
        )
        for row in active.scalars().all():
            row.effective_to = now

        pricing = FinopsProviderPricing(
            organization_id=org_id,
            provider=provider,
            model=model,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
            currency=currency,
            effective_from=now,
            version=next_ver,
            created_by=user_id,
        )
        self.db.add(pricing)
        await self.db.flush()
        return pricing

    async def org_spend(
        self,
        org_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        q = select(
            func.coalesce(func.sum(CostRecord.total_cost), 0.0),
            func.count(),
        ).where(
            CostRecord.organization_id == org_id,
            CostRecord.created_at >= start,
            CostRecord.created_at <= end,
        )
        if provider:
            q = q.where(CostRecord.provider == provider)
        if model:
            q = q.where(CostRecord.model == model)

        result = await self.db.execute(q)
        row = result.one()
        total = float(row[0] or 0)
        count = int(row[1] or 0)

        est_q = select(func.count()).where(
            CostRecord.organization_id == org_id,
            CostRecord.created_at >= start,
            CostRecord.created_at <= end,
            CostRecord.is_estimated.is_(True),
        )
        est_result = await self.db.execute(est_q)
        estimated_count = est_result.scalar() or 0

        cost_type = CostType.ESTIMATED if estimated_count > 0 else CostType.ACTUAL
        if count == 0:
            cost_type = CostType.UNKNOWN

        return {
            "total_cost": total,
            "request_count": count,
            "cost_type": cost_type,
            "estimated_records": estimated_count,
        }
