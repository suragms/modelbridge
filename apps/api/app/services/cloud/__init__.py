"""Cloud platform services."""

from app.services.cloud.config_scope import ConfigScopeService
from app.services.cloud.discovery import ServiceDiscovery
from app.services.cloud.health import CloudHealthService
from app.services.cloud.incidents import IncidentService
from app.services.cloud.instances import CloudInstanceService
from app.services.cloud.metering import MeteringService
from app.services.cloud.onboarding import CloudOnboardingService
from app.services.cloud.quotas import QuotaService
from app.services.cloud.regions import RegionService
from app.services.cloud.rollouts import RolloutService

__all__ = [
    "ConfigScopeService",
    "ServiceDiscovery",
    "CloudHealthService",
    "IncidentService",
    "CloudInstanceService",
    "MeteringService",
    "CloudOnboardingService",
    "QuotaService",
    "RegionService",
    "RolloutService",
]
