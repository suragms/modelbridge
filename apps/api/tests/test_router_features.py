import uuid

import pytest

from app.models.model import Model
from app.models.provider import Provider, ProviderStatus
from app.router.engine import RoutingEngine


def _make_model(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "provider_model_id": "test-model",
        "display_name": "Test Model",
        "context_window": 4096,
        "input_price_per_1k": 0.01,
        "output_price_per_1k": 0.02,
        "supports_streaming": True,
        "supports_tools": False,
        "supports_embeddings": False,
        "supports_vision": False,
        "supports_json_mode": False,
        "is_enabled": True,
        "quality_score": 0.7,
        "provider_id": uuid.uuid4(),
    }
    defaults.update(kwargs)
    return Model(**defaults)


def _make_provider(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "name": "test-provider",
        "type": "openai",
        "base_url": "https://api.example.com/v1",
        "status": ProviderStatus.HEALTHY,
        "is_enabled": True,
        "config": {},
    }
    defaults.update(kwargs)
    return Provider(**defaults)


class TestCapabilityFiltering:
    def test_vision_capability_filters_non_vision_models(self):
        engine = RoutingEngine()
        provider = _make_provider()
        vision_model = _make_model(
            provider_model_id="vision", supports_vision=True, provider_id=provider.id
        )
        text_model = _make_model(
            provider_model_id="text", supports_vision=False, provider_id=provider.id
        )

        decision = engine.route(
            models=[vision_model, text_model],
            providers=[provider],
            strategy="quality",
            required_capabilities={"vision"},
        )
        assert decision is not None
        assert decision.model.provider_model_id == "vision"

    def test_tools_capability_filters(self):
        engine = RoutingEngine()
        provider = _make_provider()
        tools_model = _make_model(
            provider_model_id="tools", supports_tools=True, provider_id=provider.id
        )
        no_tools = _make_model(
            provider_model_id="plain", supports_tools=False, provider_id=provider.id
        )

        decision = engine.route(
            models=[tools_model, no_tools],
            providers=[provider],
            strategy="quality",
            required_capabilities={"tools"},
        )
        assert decision is not None
        assert decision.model.provider_model_id == "tools"

    def test_model_satisfies_chat_always(self):
        provider = _make_provider()
        model = _make_model(provider_id=provider.id)
        assert RoutingEngine.model_satisfies(model, {"chat"}) is True

    def test_model_satisfies_unknown_capability_ignored(self):
        provider = _make_provider()
        model = _make_model(provider_id=provider.id)
        assert RoutingEngine.model_satisfies(model, {"hologram"}) is True


class TestOfflineFiltering:
    def test_offline_provider_excluded(self):
        engine = RoutingEngine()
        offline_provider = _make_provider(status=ProviderStatus.OFFLINE)
        healthy_provider = _make_provider(name="healthy")

        m1 = _make_model(provider_id=offline_provider.id)
        m2 = _make_model(provider_model_id="ok", provider_id=healthy_provider.id)

        decision = engine.route(
            models=[m1, m2],
            providers=[offline_provider, healthy_provider],
            strategy="quality",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "ok"


class TestRoundRobin:
    def test_rotates_across_candidates(self):
        engine = RoutingEngine()
        provider = _make_provider()
        a = _make_model(provider_model_id="a", provider_id=provider.id)
        b = _make_model(provider_model_id="b", provider_id=provider.id)
        c = _make_model(provider_model_id="c", provider_id=provider.id)

        selected = set()
        for i in range(3):
            decision = engine.route(
                models=[a, b, c],
                providers=[provider],
                strategy="round_robin",
                request_count=i,
            )
            selected.add(decision.model.provider_model_id)
        # Three distinct requests rotated to at least the distinct models.
        assert selected == {"a", "b", "c"}

    def test_request_count_drives_head(self):
        engine = RoutingEngine()
        provider = _make_provider()
        a = _make_model(provider_model_id="a", provider_id=provider.id)
        b = _make_model(provider_model_id="b", provider_id=provider.id)

        decision = engine.route(
            models=[a, b], providers=[provider], strategy="round_robin", request_count=1
        )
        assert decision.model.provider_model_id == "b"


class TestPriorityStrategy:
    def test_priority_order_respected(self):
        engine = RoutingEngine()
        provider = _make_provider()
        a = _make_model(provider_model_id="a", provider_id=provider.id)
        b = _make_model(provider_model_id="b", provider_id=provider.id)

        decision = engine.route(
            models=[a, b],
            providers=[provider],
            strategy="priority",
            policy_config={"priority_model_ids": ["b", "a"]},
        )
        assert decision.model.provider_model_id == "b"

    def test_unlisted_sorts_below_listed(self):
        engine = RoutingEngine()
        provider = _make_provider()
        listed = _make_model(provider_model_id="listed", provider_id=provider.id)
        unlisted = _make_model(provider_model_id="unlisted", provider_id=provider.id)

        decision = engine.route(
            models=[listed, unlisted],
            providers=[provider],
            strategy="priority",
            policy_config={"priority_model_ids": ["listed"]},
        )
        assert decision.model.provider_model_id == "listed"


class TestBalancedWeights:
    def test_weights_accept_empty_provider_pool(self):
        engine = RoutingEngine()
        # No candidates -> no decision, no crash.
        assert engine.route(models=[], providers=[], strategy="balanced") is None


class TestFallbackChain:
    def test_fallback_order_populated(self):
        engine = RoutingEngine()
        provider = _make_provider()
        a = _make_model(provider_model_id="a", provider_id=provider.id)
        b = _make_model(provider_model_id="b", provider_id=provider.id)
        c = _make_model(provider_model_id="c", provider_id=provider.id)

        decision = engine.route(
            models=[a, b, c], providers=[provider], strategy="round_robin", request_count=0
        )
        assert decision is not None
        assert decision.candidates_count == 3
        assert str(decision.model.id) in decision.fallback_order or len(decision.fallback_order) == 2
        # fallback_order should contain the two models after the selected head.
        assert len(decision.fallback_order) == 2


class TestPrivacyFirst:
    def test_local_preferred(self):
        engine = RoutingEngine()
        local = _make_provider(name="ollama", type="ollama")
        cloud = _make_provider(name="cloud", type="openai")
        local_model = _make_model(provider_model_id="llama", provider_id=local.id)
        cloud_model = _make_model(provider_model_id="gpt", provider_id=cloud.id)

        decision = engine.route(
            models=[local_model, cloud_model],
            providers=[local, cloud],
            strategy="privacy_first",
            policy_config={"trusted_providers": []},
        )
        assert decision.model.provider_model_id == "llama"

    def test_trusted_provider_ranked_above_unknown(self):
        engine = RoutingEngine()
        trusted = _make_provider(name="Acme")
        other = _make_provider(name="Other")
        t_model = _make_model(provider_model_id="trusted", provider_id=trusted.id)
        o_model = _make_model(provider_model_id="other", provider_id=other.id)

        decision = engine.route(
            models=[t_model, o_model],
            providers=[trusted, other],
            strategy="privacy_first",
            policy_config={"trusted_providers": ["Acme"]},
        )
        assert decision.model.provider_model_id == "trusted"


class TestCandidateMetadata:
    def test_ordered_candidates_sets_metadata(self):
        engine = RoutingEngine()
        provider = _make_provider()
        m = _make_model(
            provider_model_id="m",
            input_price_per_1k=0.001,
            output_price_per_1k=0.002,
            provider_id=provider.id,
        )

        ordered = engine.ordered_candidates(
            models=[m], providers=[provider], strategy="cheapest"
        )
        assert len(ordered) == 1
        assert ordered[0].cost_per_1k == pytest.approx(0.003)

    def test_candidate_metadata_latency(self):
        engine = RoutingEngine()
        provider = _make_provider()
        m = _make_model(provider_model_id="m", provider_id=provider.id)
        model_id = str(m.id)
        engine.record_latency(model_id, 50.0)

        ordered = engine.ordered_candidates([m], [provider], strategy="fastest")
        assert ordered[0].latency_ms == pytest.approx(50.0)

    def test_default_latency_when_no_observation(self):
        engine = RoutingEngine()
        provider = _make_provider()
        m = _make_model(provider_model_id="m", provider_id=provider.id)
        ordered = engine.ordered_candidates([m], [provider], strategy="fastest")
        assert ordered[0].latency_ms == engine.DEFAULT_LATENCY_MS
