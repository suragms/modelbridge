"""Chargeback and showback reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import CostType, FinopsChargebackReport, FinopsCostAttribution
from app.models.request_log import CostRecord


class ChargebackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_showback(
        self,
        org_id: uuid.UUID,
        *,
        period_start: datetime,
        period_end: datetime,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        department: str | None = None,
    ) -> FinopsChargebackReport:
        q = (
            select(
                FinopsCostAttribution.project_id,
                FinopsCostAttribution.team,
                func.sum(CostRecord.total_cost),
                func.count(),
            )
            .join(CostRecord, CostRecord.request_id == FinopsCostAttribution.request_id)
            .where(
                FinopsCostAttribution.organization_id == org_id,
                CostRecord.created_at >= period_start,
                CostRecord.created_at <= period_end,
            )
            .group_by(
                FinopsCostAttribution.project_id,
                FinopsCostAttribution.team,
            )
        )
        if project_id:
            q = q.where(FinopsCostAttribution.project_id == project_id)

        result = await self.db.execute(q)
        rows = result.all()

        if not rows:
            total_q = await self.db.execute(
                select(func.coalesce(func.sum(CostRecord.total_cost), 0.0), func.count()).where(
                    CostRecord.organization_id == org_id,
                    CostRecord.created_at >= period_start,
                    CostRecord.created_at <= period_end,
                )
            )
            total_row = total_q.one()
            breakdown = {"organization_total": float(total_row[0] or 0), "requests": int(total_row[1] or 0)}
            total_cost = float(total_row[0] or 0)
        else:
            breakdown = {
                "by_project": [
                    {
                        "project_id": str(r[0]) if r[0] else None,
                        "team": r[1],
                        "cost": float(r[2] or 0),
                        "requests": int(r[3] or 0),
                    }
                    for r in rows
                ]
            }
            total_cost = sum(float(r[2] or 0) for r in rows)

        report = FinopsChargebackReport(
            organization_id=org_id,
            report_type="showback",
            period_start=period_start,
            period_end=period_end,
            department=department,
            project_id=project_id,
            total_cost=total_cost,
            cost_type=CostType.ESTIMATED,
            breakdown=breakdown,
            generated_by=user_id,
        )
        self.db.add(report)
        await self.db.flush()
        return report

    async def list_reports(self, org_id: uuid.UUID, limit: int = 20) -> list[FinopsChargebackReport]:
        result = await self.db.execute(
            select(FinopsChargebackReport)
            .where(FinopsChargebackReport.organization_id == org_id)
            .order_by(FinopsChargebackReport.generated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
