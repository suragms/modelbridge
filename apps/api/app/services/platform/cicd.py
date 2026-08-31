"""Provider-neutral CI/CD integration abstraction."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class PipelineStage(enum.StrEnum):
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    STATUS = "status"


class PipelineStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineEvent:
    provider: str
    stage: PipelineStage
    status: PipelineStatus
    external_id: str
    repository: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CICDAdapter:
    """Base adapter for CI/CD providers."""

    provider: str = "generic"

    def normalize_event(self, raw: dict) -> PipelineEvent | None:
        raise NotImplementedError


class GitHubActionsAdapter(CICDAdapter):
    provider = "github"

    def normalize_event(self, raw: dict) -> PipelineEvent | None:
        action = raw.get("action")
        workflow_run = raw.get("workflow_run") or {}
        repo = (raw.get("repository") or {}).get("full_name")
        conclusion = workflow_run.get("conclusion") or "pending"
        status_map = {
            "success": PipelineStatus.SUCCESS,
            "failure": PipelineStatus.FAILED,
            "cancelled": PipelineStatus.CANCELLED,
            "in_progress": PipelineStatus.RUNNING,
            None: PipelineStatus.PENDING,
        }
        return PipelineEvent(
            provider=self.provider,
            stage=PipelineStage.STATUS,
            status=status_map.get(conclusion if action == "completed" else workflow_run.get("status"), PipelineStatus.PENDING),
            external_id=str(workflow_run.get("id", "")),
            repository=repo,
            branch=(workflow_run.get("head_branch")),
            commit_sha=(workflow_run.get("head_sha")),
            metadata={"event": "workflow_run", "action": action},
        )


class CICDRegistry:
    _adapters: dict[str, CICDAdapter] = {
        "github": GitHubActionsAdapter(),
    }

    @classmethod
    def get(cls, provider: str) -> CICDAdapter | None:
        return cls._adapters.get(provider)

    @classmethod
    def normalize(cls, provider: str, raw: dict) -> PipelineEvent | None:
        adapter = cls.get(provider)
        if not adapter:
            return None
        return adapter.normalize_event(raw)
