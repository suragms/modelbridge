"""Enterprise collaboration services."""

from app.services.enterprise.access import assert_project_access, assert_workspace_access, get_project, get_workspace
from app.services.enterprise.activity import record_activity
from app.services.enterprise.config import ConfigurationService, safe_diff
from app.services.enterprise.fleet import FleetService

__all__ = [
    "assert_project_access",
    "assert_workspace_access",
    "get_project",
    "get_workspace",
    "record_activity",
    "ConfigurationService",
    "safe_diff",
    "FleetService",
]
