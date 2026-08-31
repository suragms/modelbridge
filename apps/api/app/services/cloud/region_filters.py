"""Region and data residency filters for routing targets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.cloud import DataResidencyPolicy, Region
from app.models.provider import Provider
from app.services.cloud.regions import RegionService

if TYPE_CHECKING:
    from app.services.routing import RouteTarget

RESIDENCY_ZONE_MAP = {
    DataResidencyPolicy.EU_ONLY: {"eu", "eu_only", "europe"},
    DataResidencyPolicy.US_ONLY: {"us", "us_only", "north_america"},
    DataResidencyPolicy.INDIA_ONLY: {"in", "india", "india_only"},
}


def provider_matches_residency(provider: Provider, policy: str) -> bool:
    if not policy or policy == DataResidencyPolicy.GLOBAL:
        return True
    residency = (provider.data_residency or "").lower()
    region = (provider.region or "").lower()
    allowed = RESIDENCY_ZONE_MAP.get(policy, set())
    if residency in allowed or region in allowed:
        return True
    return False


def filter_targets_by_region(
    targets: list[RouteTarget],
    *,
    region: Region | None,
    data_residency_policy: str | None,
    region_service: RegionService | None = None,
) -> list[RouteTarget]:
    if not targets:
        return targets

    filtered: list[RouteTarget] = []
    for target in targets:
        provider = target.provider
        if region and region_service:
            if not region_service.eligible_for_routing(region):
                continue
            if data_residency_policy and not region_service.residency_matches(region, data_residency_policy):
                continue
        if data_residency_policy and not provider_matches_residency(provider, data_residency_policy):
            continue
        if region and provider.region and provider.region.lower() != region.code.lower():
            if region.code != "local":
                continue
        filtered.append(target)
    return filtered if filtered else targets
