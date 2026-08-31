"""Studio deployment pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import Environment, EnvironmentKind
from app.models.studio import StudioDeployment, StudioDeploymentStatus


class DeploymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        resource_type: str,
        resource_id: uuid.UUID,
        version_id: uuid.UUID | None,
        environment_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
    ) -> StudioDeployment:
        deployment = StudioDeployment(
            organization_id=org_id,
            name=name,
            resource_type=resource_type,
            resource_id=resource_id,
            version_id=version_id,
            environment_id=environment_id,
            status=StudioDeploymentStatus.DRAFT,
            requested_by=user_id,
            pipeline_state={"steps": ["draft"]},
        )
        self.db.add(deployment)
        await self.db.flush()
        return deployment

    async def validate(self, deployment: StudioDeployment) -> StudioDeployment:
        deployment.status = StudioDeploymentStatus.VALIDATING
        state = deployment.pipeline_state or {}
        steps = list(state.get("steps") or [])
        steps.append("validate")
        deployment.pipeline_state = {**state, "steps": steps, "validation": "passed"}
        deployment.status = StudioDeploymentStatus.TESTING
        await self.db.flush()
        return deployment

    async def request_approval(self, deployment: StudioDeployment) -> StudioDeployment:
        env = await self.db.get(Environment, deployment.environment_id) if deployment.environment_id else None
        if env and env.kind == EnvironmentKind.PRODUCTION:
            deployment.status = StudioDeploymentStatus.AWAITING_APPROVAL
        else:
            deployment.status = StudioDeploymentStatus.DEPLOYING
        state = deployment.pipeline_state or {}
        steps = list(state.get("steps") or [])
        steps.append("approval_requested")
        deployment.pipeline_state = {**state, "steps": steps}
        await self.db.flush()
        return deployment

    async def approve(self, deployment: StudioDeployment, approver_id: uuid.UUID) -> StudioDeployment:
        if deployment.status != StudioDeploymentStatus.AWAITING_APPROVAL:
            raise ValueError("Deployment is not awaiting approval")
        deployment.status = StudioDeploymentStatus.DEPLOYING
        deployment.approved_by = approver_id
        deployment.approved_at = datetime.now(UTC)
        await self.db.flush()
        return deployment

    async def deploy(self, deployment: StudioDeployment) -> StudioDeployment:
        deployment.status = StudioDeploymentStatus.DEPLOYED
        deployment.deployed_at = datetime.now(UTC)
        state = deployment.pipeline_state or {}
        steps = list(state.get("steps") or [])
        steps.append("deployed")
        deployment.pipeline_state = {**state, "steps": steps}
        await self.db.flush()
        return deployment

    async def reject(self, deployment: StudioDeployment, reason: str) -> StudioDeployment:
        deployment.status = StudioDeploymentStatus.REJECTED
        state = deployment.pipeline_state or {}
        deployment.pipeline_state = {**state, "rejection_reason": reason}
        await self.db.flush()
        return deployment

    async def get(self, org_id: uuid.UUID, deployment_id: uuid.UUID) -> StudioDeployment | None:
        d = await self.db.get(StudioDeployment, deployment_id)
        if not d or d.organization_id != org_id:
            return None
        return d
