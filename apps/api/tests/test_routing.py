import uuid

from app.models.model import Model
from app.models.provider import Provider
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
        "status": "healthy",
        "is_enabled": True,
        "config": {},
    }
    defaults.update(kwargs)
    return Provider(**defaults)


class TestRoutingEngine:
    def test_balanced_strategy_selects_best_model(self):
        engine = RoutingEngine()

        provider = _make_provider()
        cheap_model = _make_model(
            provider_model_id="cheap",
            input_price_per_1k=0.001,
            output_price_per_1k=0.002,
            quality_score=0.5,
            provider_id=provider.id,
        )
        expensive_model = _make_model(
            provider_model_id="expensive",
            input_price_per_1k=0.1,
            output_price_per_1k=0.2,
            quality_score=0.9,
            provider_id=provider.id,
        )

        decision = engine.route(
            models=[cheap_model, expensive_model],
            providers=[provider],
            strategy="balanced",
        )
        assert decision is not None
        assert decision.model is not None

    def test_cheapest_strategy_selects_lowest_price(self):
        engine = RoutingEngine()

        provider = _make_provider()
        cheap_model = _make_model(
            provider_model_id="cheap",
            input_price_per_1k=0.001,
            output_price_per_1k=0.002,
            provider_id=provider.id,
        )
        expensive_model = _make_model(
            provider_model_id="expensive",
            input_price_per_1k=0.1,
            output_price_per_1k=0.2,
            provider_id=provider.id,
        )

        decision = engine.route(
            models=[cheap_model, expensive_model],
            providers=[provider],
            strategy="cheapest",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "cheap"

    def test_quality_strategy_selects_highest_quality(self):
        engine = RoutingEngine()

        provider = _make_provider()
        low_quality = _make_model(
            provider_model_id="low",
            quality_score=0.3,
            provider_id=provider.id,
        )
        high_quality = _make_model(
            provider_model_id="high",
            quality_score=0.95,
            provider_id=provider.id,
        )

        decision = engine.route(
            models=[low_quality, high_quality],
            providers=[provider],
            strategy="quality",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "high"

    def test_disabled_model_excluded(self):
        engine = RoutingEngine()

        provider = _make_provider()
        disabled_model = _make_model(
            provider_model_id="disabled",
            is_enabled=False,
            provider_id=provider.id,
        )
        enabled_model = _make_model(
            provider_model_id="enabled",
            is_enabled=True,
            provider_id=provider.id,
        )

        decision = engine.route(
            models=[disabled_model, enabled_model],
            providers=[provider],
            strategy="quality",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "enabled"

    def test_disabled_provider_excluded(self):
        engine = RoutingEngine()

        disabled_provider = _make_provider(is_enabled=False)
        enabled_provider = _make_provider(name="enabled-provider")

        model1 = _make_model(provider_id=disabled_provider.id)
        model2 = _make_model(provider_model_id="enabled", provider_id=enabled_provider.id)

        decision = engine.route(
            models=[model1, model2],
            providers=[disabled_provider, enabled_provider],
            strategy="quality",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "enabled"

    def test_empty_models_returns_none(self):
        engine = RoutingEngine()
        provider = _make_provider()
        decision = engine.route(models=[], providers=[provider], strategy="balanced")
        assert decision is None

    def test_local_only_strategy(self):
        engine = RoutingEngine()

        ollama_provider = _make_provider(name="ollama", type="ollama")
        openai_provider = _make_provider(name="openai", type="openai")

        ollama_model = _make_model(provider_model_id="llama3", provider_id=ollama_provider.id)
        gpt_model = _make_model(provider_model_id="gpt-4", provider_id=openai_provider.id)

        decision = engine.route(
            models=[ollama_model, gpt_model],
            providers=[ollama_provider, openai_provider],
            strategy="local_only",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "llama3"

    def test_latency_tracking(self):
        engine = RoutingEngine()
        model_id = str(uuid.uuid4())

        engine.record_latency(model_id, 100.0)
        engine.record_latency(model_id, 200.0)
        avg = engine.get_avg_latency(model_id)
        assert avg == 150.0

    def test_fallback_provider_selection(self):
        engine = RoutingEngine()

        provider1 = _make_provider(name="primary")
        provider2 = _make_provider(name="fallback")

        model1 = _make_model(provider_model_id="primary-model", provider_id=provider1.id)
        model2 = _make_model(provider_model_id="fallback-model", provider_id=provider2.id)

        # Disable primary
        provider1.is_enabled = False

        decision = engine.route(
            models=[model1, model2],
            providers=[provider1, provider2],
            strategy="balanced",
        )
        assert decision is not None
        assert decision.model.provider_model_id == "fallback-model"
