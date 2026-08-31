"""Recommendation lifecycle with audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import (
    AutomationLevel,
    IntelligenceRecommendation,
    RecommendationAction,
    RecommendationStatus,
)
from app.services.metrics import record_recommendation_action, record_recommendation_created


class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        category: str,
        title: str,
        description: str,
        evidence: dict,
        suggested_action: str | None = None,
        confidence: float = 0.5,
        severity: str = "medium",
        risks: str | None = None,
        policy_constraints: dict | None = None,
        automation_level: str = AutomationLevel.RECOMMEND,
        dedupe_key: str | None = None,
    ) -> IntelligenceRecommendation:
        if dedupe_key:
            existing = await self.db.execute(
                select(IntelligenceRecommendation).where(
                    IntelligenceRecommendation.organization_id == organization_id,
                    IntelligenceRecommendation.title == title,
                    IntelligenceRecommendation.status == RecommendationStatus.OPEN,
                )
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        rec = IntelligenceRecommendation(
            organization_id=organization_id,
            category=category,
            severity=severity,
            title=title,
            description=description,
            evidence=evidence,
            suggested_action=suggested_action,
            confidence=confidence,
            risks=risks,
            policy_constraints=policy_constraints,
            automation_level=automation_level,
            status=RecommendationStatus.OPEN,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        self.db.add(rec)
        record_recommendation_created(category=category)
        await self.db.flush()
        return rec

    async def list_recommendations(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[IntelligenceRecommendation]:
        q = (
            select(IntelligenceRecommendation)
            .where(IntelligenceRecommendation.organization_id == organization_id)
            .order_by(IntelligenceRecommendation.created_at.desc())
            .limit(limit)
        )
        if status:
            q = q.where(IntelligenceRecommendation.status == status)
        if category:
            q = q.where(IntelligenceRecommendation.category == category)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get(self, organization_id: uuid.UUID, rec_id: uuid.UUID) -> IntelligenceRecommendation | None:
        rec = await self.db.get(IntelligenceRecommendation, rec_id)
        if not rec or rec.organization_id != organization_id:
            return None
        return rec

    async def transition(
        self,
        rec: IntelligenceRecommendation,
        action: str,
        *,
        actor_id: uuid.UUID | None,
        notes: str | None = None,
    ) -> IntelligenceRecommendation:
        transitions = {
            "acknowledge": RecommendationStatus.ACKNOWLEDGED,
            "approve": RecommendationStatus.APPROVED,
            "dismiss": RecommendationStatus.DISMISSED,
            "implement": RecommendationStatus.IMPLEMENTED,
        }
        if action not in transitions:
            raise ValueError(f"Unknown action: {action}")

        if action == "approve" and rec.automation_level == AutomationLevel.OBSERVE_ONLY:
            raise ValueError("This recommendation is observe-only and cannot be approved for action")

        rec.status = transitions[action]
        rec.updated_at = datetime.now(UTC)

        self.db.add(
            RecommendationAction(
                recommendation_id=rec.id,
                organization_id=rec.organization_id,
                action=action,
                actor_id=actor_id,
                notes=notes,
            )
        )
        record_recommendation_action(action=action)
        await self.db.flush()
        return rec
