"""Phase 12 cloud architecture tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.cloud import ConfigScope, DataResidencyPolicy, InstanceLifecycleStatus, RegionStatus
from app.models.provider import Provider, ProviderType
from app.services.cloud.config_scope import ConfigScopeService, deepcopy_merge
from app.services.cloud.metering import MeteringService, sanitize_metadata
from app.services.cloud.quotas import QuotaExceeded, QuotaService
from app.services.cloud.regions import RegionService
from app.services.cloud.region_filters import provider_matches_residency
from app.services.cloud.instances import LIFECYCLE_TRANSITIONS
from app.services.cloud.onboarding import ONBOARDING_STEPS


class TestConfigPrecedence:
    def test_deepcopy_merge_nested(self):
        base = {"routing": {"strategy": "auto"}, "limits": {"max": 100}}
        overlay = {"routing": {"strategy": "cheapest"}}
        merged = deepcopy_merge(base, overlay)
        assert merged["routing"]["strategy"] == "cheapest"
        assert merged["limits"]["max"] == 100


class TestRegionResidency:
    def test_global_always_matches(self):
        from app.models.cloud import Region

        region = Region(code="local", name="Local", data_residency_zones=["global"])
        svc = RegionService(None)  # type: ignore[arg-type]
        assert svc.residency_matches(region, DataResidencyPolicy.GLOBAL)

    def test_eu_requires_zone(self):
        from app.models.cloud import Region

        region = Region(code="eu-west", name="EU", data_residency_zones=["eu"])
        svc = RegionService(None)  # type: ignore[arg-type]
        assert svc.residency_matches(region, DataResidencyPolicy.EU_ONLY)
        region2 = Region(code="us-east", name="US", data_residency_zones=["us"])
        assert not svc.residency_matches(region2, DataResidencyPolicy.EU_ONLY)

    def test_provider_residency_metadata(self):
        provider = Provider(name="p", type=ProviderType.OPENAI, data_residency="eu")
        assert provider_matches_residency(provider, DataResidencyPolicy.EU_ONLY)
        provider2 = Provider(name="p2", type=ProviderType.OPENAI, data_residency="us")
        assert not provider_matches_residency(provider2, DataResidencyPolicy.EU_ONLY)


class TestLifecycleTransitions:
    def test_provisioning_to_active_allowed(self):
        allowed = LIFECYCLE_TRANSITIONS[InstanceLifecycleStatus.PROVISIONING]
        assert InstanceLifecycleStatus.ACTIVE in allowed

    def test_decommissioned_terminal(self):
        assert LIFECYCLE_TRANSITIONS[InstanceLifecycleStatus.DECOMMISSIONED] == set()


class TestMeteringMetadata:
    def test_sensitive_keys_stripped(self):
        meta = sanitize_metadata({"provider": "openai", "password": "secret", "api_key": "x"})
        assert meta == {"provider": "openai"}


class TestOnboardingSteps:
    def test_steps_defined(self):
        assert "region" in ONBOARDING_STEPS
        assert ONBOARDING_STEPS[0] == "organization"


class TestRegionRoutingEligibility:
    def test_disabled_region_not_eligible(self):
        from app.models.cloud import Region

        region = Region(code="x", name="X", status=RegionStatus.DISABLED)
        svc = RegionService(None)  # type: ignore[arg-type]
        assert not svc.eligible_for_routing(region)

    def test_active_region_eligible(self):
        from app.models.cloud import Region

        region = Region(code="x", name="X", status=RegionStatus.ACTIVE)
        svc = RegionService(None)  # type: ignore[arg-type]
        assert svc.eligible_for_routing(region)


class TestQuotaLogic:
    def test_quota_exceeded_exception(self):
        exc = QuotaExceeded("requests", 100, 101)
        assert exc.resource == "requests"
        assert exc.limit == 100
