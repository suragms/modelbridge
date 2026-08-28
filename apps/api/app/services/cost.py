from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import CostRecord
from app.services.pricing import PricingRegistry


class CostService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing = PricingRegistry(db)

    async def estimate_and_log(
        self,
        request_id: str,
        model_name: str,
        provider_name: str,
        input_tokens: int,
        output_tokens: int,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> CostRecord:
        pricing = await self.pricing.get_pricing(model_name)
        input_cost, output_cost, total_cost, is_estimated = PricingRegistry.calculate_cost(
            input_tokens, output_tokens, pricing
        )

        if not pricing.is_known:
            is_estimated = True

        cost_record = CostRecord(
            request_id=request_id,
            model=model_name,
            provider=provider_name,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            is_estimated=is_estimated,
            pricing_source=pricing.pricing_source,
            currency=pricing.currency,
            user_id=user_id,
            organization_id=organization_id,
        )
        self.db.add(cost_record)
        await self.db.flush()
        return cost_record

    async def get_total_cost(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        query = select(func.sum(CostRecord.total_cost))
        conditions = []
        if user_id:
            conditions.append(CostRecord.user_id == user_id)
        if organization_id:
            conditions.append(CostRecord.organization_id == organization_id)
        if start_date:
            conditions.append(CostRecord.created_at >= start_date)
        if end_date:
            conditions.append(CostRecord.created_at <= end_date)
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0.0
