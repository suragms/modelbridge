from app.api.routes.agents import router as agents_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.embeddings import router as embeddings_router
from app.api.routes.governance import router as governance_router
from app.api.routes.logs import router as logs_router
from app.api.routes.models import router as models_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.playground import router as playground_router
from app.api.routes.providers import router as providers_router
from app.api.routes.routing import router as routing_router

from app.api.routes.extensions import router as extensions_router
from app.api.routes.templates import router as templates_router
from app.api.routes.workflows import router as workflows_router

from app.api.routes.enterprise import router as enterprise_router
from app.api.routes.cloud import router as cloud_router
from app.api.routes.cloud import quotas_router
from app.api.routes.cloud import usage_router
from app.api.routes.intelligence import assistant_router as operations_assistant_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.quality import router as quality_router
from app.api.routes.studio import (
    evaluation_runs_router,
    evaluations_router,
    prompts_router,
    router as studio_router,
)
from app.api.routes.marketplace import admin_router as marketplace_admin_router
from app.api.routes.marketplace import publishers_router
from app.api.routes.marketplace import router as marketplace_router
from app.api.routes.platform import (
    automations_router,
    developer_router,
    events_router,
    integrations_router,
    webhooks_router,
)
from app.api.routes.fleet import control_router as control_plane_router
from app.api.routes.fleet import router as fleet_router
from app.api.routes.projects import env_router as environments_router
from app.api.routes.projects import router as projects_router
from app.api.routes.workspaces import router as workspaces_router

__all__ = [
    "auth_router",
    "providers_router",
    "models_router",
    "chat_router",
    "embeddings_router",
    "playground_router",
    "api_keys_router",
    "logs_router",
    "analytics_router",
    "routing_router",
    "audit_router",
    "organizations_router",
    "governance_router",
    "agents_router",
    "workflows_router",
    "extensions_router",
    "templates_router",
    "workspaces_router",
    "projects_router",
    "environments_router",
    "enterprise_router",
    "cloud_router",
    "usage_router",
    "quotas_router",
    "intelligence_router",
    "operations_assistant_router",
    "events_router",
    "webhooks_router",
    "integrations_router",
    "automations_router",
    "developer_router",
    "marketplace_router",
    "publishers_router",
    "marketplace_admin_router",
    "studio_router",
    "prompts_router",
    "evaluations_router",
    "evaluation_runs_router",
    "quality_router",
    "fleet_router",
    "control_plane_router",
]
