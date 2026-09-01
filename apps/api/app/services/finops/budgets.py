"""FinOps budget management with threshold events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import (
    BudgetPeriod,
    CostType,
    EnforcementAction,
    FinopsBudget,
    FinopsBudgetEvent,
    FinopsGovernanceAudit,
)
from app.services.finops.engine import CostEngine
from app.services.metrics import record_finops_budget_threshold
from app.services.platform.events import EventBus


class BudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = CostEngine(db)

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        amount: float,
        scope: str = "organization",
        scope_id: uuid.UUID | None = None,
        currency: str = "USD",
        period: str = BudgetPeriod.MONTHLY,
        thresholds: list[int] | None = None,
        enforcement_action: str = EnforcementAction.ALERT,
        user_id: uuid.UUID | None = None,
    ) -> FinopsBudget:
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = None
        if period == BudgetPeriod.MONTHLY:
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        elif period == BudgetPeriod.QUARTERLY:
            end = start + timedelta(days=90)
        elif period == BudgetPeriod.YEARLY:
            end = start.replace(year=start.year + 1)

        budget = FinopsBudget(
            organization_id=org_id,
            name=name,
            scope=scope,
            scope_id=scope_id,
            amount=amount,
            currency=currency,
            period=period,
            start_date=start,
            end_date=end,
            thresholds=thresholds or [50, 75, 90, 100],
            enforcement_action=enforcement_action,
            created_by=user_id,
        )
        self.db.add(budget)
        await self._audit(org_id, user_id, f"budget:{scope}", "create", {"budget_name": name, "amount": amount})
        await self.db.flush()
        return budget

    async def list_budgets(self, org_id: uuid.UUID) -> list[FinopsBudget]:
        result = await self.db.execute(
            select(FinopsBudget)
            .where(FinopsBudget.organization_id == org_id, FinopsBudget.enabled.is_(True))
            .order_by(FinopsBudget.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_budget(self, org_id: uuid.UUID, budget_id: uuid.UUID) -> FinopsBudget | None:
        b = await self.db.get(FinopsBudget, budget_id)
        if not b or b.organization_id != org_id:
            return None
        return b

    async def check_thresholds(self, budget: FinopsBudget) -> list[FinopsBudgetEvent]:
        spend_data = await self.engine.org_spend(
            budget.organization_id,
            start=budget.start_date,
            end=budget.end_date or datetime.now(UTC),
        )
        spend = spend_data["total_cost"]
        cost_type = spend_data["cost_type"]
        if budget.amount <= 0:
            return []

        pct = (spend / budget.amount) * 100
        events: list[FinopsBudgetEvent] = []
        for threshold in sorted(budget.thresholds or []):
            if pct < threshold:
                continue
            existing = await self.db.execute(
                select(FinopsBudgetEvent).where(
                    FinopsBudgetEvent.budget_id == budget.id,
                    FinopsBudgetEvent.threshold_percent == threshold,
                    FinopsBudgetEvent.created_at >= budget.start_date,
                )
            )
            if existing.scalar_one_or_none():
                continue

            msg = (
                f"Budget '{budget.name}' reached {threshold}% "
                f"(${spend:.4f} of ${budget.amount:.2f}). "
                f"Cost type: {cost_type} — not exact provider billing."
            )
            event = FinopsBudgetEvent(
                organization_id=budget.organization_id,
                budget_id=budget.id,
                threshold_percent=threshold,
                current_spend=spend,
                budget_amount=budget.amount,
                cost_type=cost_type,
                message=msg,
            )
            self.db.add(event)
            events.append(event)
            record_finops_budget_threshold(status=str(threshold))

            event_type = "budget.limit.reached" if threshold >= 100 else "budget.threshold.crossed"
            await EventBus(self.db).emit(
                organization_id=budget.organization_id,
                event_type=event_type,
                data={"status": str(threshold), "execution_id": str(budget.id)},
                source="finops",
            )

        await self.db.flush()
        return events

    async def budget_status(self, budget: FinopsBudget) -> dict:
        spend_data = await self.engine.org_spend(
            budget.organization_id,
            start=budget.start_date,
            end=budget.end_date or datetime.now(UTC),
        )
        spend = spend_data["total_cost"]
        pct = (spend / budget.amount * 100) if budget.amount > 0 else 0
        return {
            "budget_id": str(budget.id),
            "name": budget.name,
            "amount": budget.amount,
            "current_spend": spend,
            "utilization_percent": round(pct, 2),
            "cost_type": spend_data["cost_type"],
            "status": "exceeded" if pct >= 100 else ("warning" if pct >= 75 else "ok"),
            "enforcement_action": budget.enforcement_action,
        }

    async def _audit(
        self,
        org_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        scope: str,
        action: str,
        details: dict,
        reason: str | None = None,
    ) -> None:
        self.db.add(
            FinopsGovernanceAudit(
                organization_id=org_id,
                actor_id=actor_id,
                scope=scope,
                action=action,
                reason=reason,
                details=details,
            )
        )
