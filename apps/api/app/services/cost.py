from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.models.request_log import CostRecord


class CostService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        input_cost = 0.0
        output_cost = 0.0
        is_estimated = True

        query = select(Model).where(Model.provider_model_id == model_name)
        result = await self.db.execute(query)
        model_record = result.scalar_one_or_none()

        if model_record:
            input_cost = (input_tokens / 1000) * model_record.input_price_per_1k
            output_cost = (output_tokens / 1000) * model_record.output_price_per_1k
            if model_record.input_price_per_1k == 0 and model_record.output_price_per_1k == 0:
                is_estimated = False

        cost_record = CostRecord(
            request_id=request_id,
            model=model_name,
            provider=provider_name,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            is_estimated=is_estimated,
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
    ) -> float:
        query = select(func.sum(CostRecord.total_cost))
        if user_id:
            query = query.where(CostRecord.user_id == user_id)
        if organization_id:
            query = query.where(CostRecord.organization_id == organization_id)

        result = await self.db.execute(query)
        return result.scalar() or 0.0
