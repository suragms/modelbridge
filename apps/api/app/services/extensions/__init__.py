"""Extension ecosystem services."""

from app.services.extensions.lifecycle import ExtensionLifecycleService
from app.services.extensions.registry import ExtensionRegistryService, seed_official_packages

__all__ = [
    "ExtensionLifecycleService",
    "ExtensionRegistryService",
    "seed_official_packages",
]
