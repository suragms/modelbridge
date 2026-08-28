"""Routing engine: given incoming requests, available models and provider
health, selects the best model/provider for a configured strategy.

The engine is provider-agnostic: it works entirely on the ``Model`` /
``Provider`` ORM rows and never touches provider internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.model import Model
from app.models.provider import Provider, ProviderStatus
from app.services.capabilities import filter_reason, missing_capabilities

_LOCAL_PROVIDER_TYPES = {"ollama", "lmstudio"}


@dataclass
class CandidateModel:
    model: Model
    provider: Provider
    score: float = 0.0
    latency_ms: float = 0.0
    cost_per_1k: float = 0.0


@dataclass
class RouteDecision:
    model: Model
    provider: Provider
    strategy: str
    reason: str = ""
    fallback_used: bool = False
    candidates_count: int = 0
    fallback_order: list[str] = field(default_factory=list)


class RoutingEngine:
    """Pure decision logic for choosing which model serves a request.

    Latency measurements are recorded per model id so the ``fastest`` /
    ``balanced`` strategies use real observations rather than invented numbers.
    When no measurement exists a documented default latency is used.
    """

    # Used when no real latency has been recorded for a model (documented
    # fallback for the fastest/balanced strategies).
    DEFAULT_LATENCY_MS = 1000.0

    def __init__(self):
        self._latency_cache: dict[str, list[float]] = {}
        self._round_robin_index: dict[str, int] = {}

    # ---- latency observation -------------------------------------------------

    def record_latency(self, model_id: str, latency_ms: float) -> None:
        if model_id not in self._latency_cache:
            self._latency_cache[model_id] = []
        cache = self._latency_cache[model_id]
        cache.append(latency_ms)
        if len(cache) > 50:
            cache.pop(0)

    def get_avg_latency(self, model_id: str) -> float:
        cache = self._latency_cache.get(model_id, [])
        if not cache:
            return self.DEFAULT_LATENCY_MS
        return sum(cache) / len(cache)

    # ---- candidate building --------------------------------------------------

    def build_candidates(
        self,
        models: list[Model],
        providers: list[Provider],
        required_capabilities: set[str] | None = None,
    ) -> list[CandidateModel]:
        """Build the ordered candidate list for a request.

        Filters out: disabled models, disabled/offline providers, and models
        that do not satisfy the required capabilities.
        """
        provider_map = {str(p.id): p for p in providers}
        required = required_capabilities or set()

        candidates: list[CandidateModel] = []
        for model in models:
            if not model.is_enabled:
                continue
            provider = provider_map.get(str(model.provider_id))
            if not provider or not provider.is_enabled:
                continue
            if provider.status == ProviderStatus.OFFLINE:
                continue
            if not self._satisfies_capabilities(model, required):
                continue
            candidates.append(CandidateModel(model=model, provider=provider))
        return candidates

    @staticmethod
    def model_satisfies(model: Model, required: set[str]) -> bool:
        """Return True when ``model`` supports every required capability."""
        return not missing_capabilities(model, required)

    @staticmethod
    def explain_filter(model: Model, provider: Provider | None, required: set[str]) -> str | None:
        return filter_reason(model, provider, required)

    @classmethod
    def _satisfies_capabilities(cls, model, required):
        # Backwards-compatible alias.
        return cls.model_satisfies(model, required)

    # ---- public entry points -------------------------------------------------

    def route(
        self,
        models: list[Model],
        providers: list[Provider],
        strategy: str = "auto",
        policy_config: dict | None = None,
        required_capabilities: set[str] | None = None,
        request_count: int | None = None,
    ) -> RouteDecision | None:
        """Select the best candidate for a single request."""
        candidates = self.build_candidates(models, providers, required_capabilities)
        strategy_fn = self._get_strategy(strategy)

        order = strategy_fn(
            candidates,
            policy_config or {},
            request_count=request_count,
        )
        if not order:
            return None

        best = order[0]
        return RouteDecision(
            model=best.model,
            provider=best.provider,
            strategy=strategy,
            candidates_count=len(candidates),
            fallback_order=[str(c.model.id) for c in order[1:]],
        )

    def ordered_candidates(
        self,
        models: list[Model],
        providers: list[Provider],
        strategy: str = "auto",
        policy_config: dict | None = None,
        required_capabilities: set[str] | None = None,
        request_count: int | None = None,
    ) -> list[CandidateModel]:
        """Return all candidates ranked by the strategy (used for routing tests
        and to build the fallback chain without mutating anything)."""
        candidates = self.build_candidates(models, providers, required_capabilities)
        strategy_fn = self._get_strategy(strategy)
        return strategy_fn(candidates, policy_config or {}, request_count=request_count)

    # ---- strategy dispatch ---------------------------------------------------

    def _get_strategy(self, strategy: str):
        strategies = {
            "auto": self._strategy_balanced,
            "balanced": self._strategy_balanced,
            "priority": self._strategy_priority,
            "cheapest": self._strategy_cheapest,
            "fastest": self._strategy_fastest,
            "quality": self._strategy_quality,
            "local_only": self._strategy_local,
            "privacy_first": self._strategy_privacy,
            "round_robin": self._strategy_round_robin,
            "least_latency": self._strategy_least_latency,
        }
        return strategies.get(strategy, self._strategy_balanced)

    @staticmethod
    def supported_strategies() -> list[str]:
        return [
            "auto",
            "balanced",
            "priority",
            "cheapest",
            "fastest",
            "quality",
            "local_only",
            "privacy_first",
            "round_robin",
            "least_latency",
        ]

    # ---- concrete strategies -------------------------------------------------

    def _strategy_balanced(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        quality_w = config.get("quality_weight", 0.35)
        speed_w = config.get("speed_weight", 0.30)
        cost_w = config.get("cost_weight", 0.20)
        reliability_w = config.get("reliability_weight", 0.15)

        for c in candidates:
            latency = self.get_avg_latency(str(c.model.id))
            speed_score = max(0.0, 1.0 - (latency / 5000))
            cost_score = max(0.0, 1.0 - (self._cost(c.model) * 100))
            reliability_score = 1.0 if c.provider.status == ProviderStatus.HEALTHY else 0.5
            c.score = (
                quality_w * c.model.quality_score
                + speed_w * speed_score
                + cost_w * cost_score
                + reliability_w * reliability_score
            )
            c.latency_ms = latency
            c.cost_per_1k = self._cost(c.model)
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_priority(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        priority_order = config.get("priority_model_ids", config.get("priority", []))
        # A priority list may reference models by internal id or by their
        # provider model name; both are honored.
        priority_map: dict[str, int] = {}
        for i, mid in enumerate(priority_order):
            priority_map.setdefault(str(mid), i)
        for c in candidates:
            idx = priority_map.get(str(c.model.id))
            if idx is None:
                idx = priority_map.get(str(c.model.provider_model_id))
            if idx is None:
                # Models not in the list sort below any configured model.
                idx = len(priority_order)
            c.score = -idx
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_cheapest(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        for c in candidates:
            c.cost_per_1k = self._cost(c.model)
            c.score = -c.cost_per_1k
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_fastest(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        for c in candidates:
            c.latency_ms = self.get_avg_latency(str(c.model.id))
            c.score = -c.latency_ms
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_least_latency(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        return self._strategy_fastest(candidates, config, request_count)

    def _strategy_quality(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        for c in candidates:
            c.score = c.model.quality_score
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_local(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        for c in candidates:
            c.score = 1.0 if c.provider.type in _LOCAL_PROVIDER_TYPES else -1.0
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_privacy(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        trusted = config.get("trusted_providers", [])
        for c in candidates:
            if c.provider.type in _LOCAL_PROVIDER_TYPES:
                c.score = 2.0
            elif c.provider.name in trusted:
                c.score = 1.0
            else:
                c.score = 0.0
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_round_robin(
        self, candidates: list[CandidateModel], config: dict, request_count: int | None = None
    ) -> list[CandidateModel]:
        """Rotate through the healthy candidates deterministically.

        One candidate id is selected as the head for this request; the rest keep
        their relative order. Uses a persistent counter so consecutive requests
        rotate across candidates (basic load balancing).
        """
        if not candidates:
            return []
        key = "|".join(str(c.model.id) for c in candidates)
        if request_count is None:
            start = self._round_robin_index.get(key, 0)
        else:
            start = request_count
        rotated = candidates[start % len(candidates):] + candidates[: start % len(candidates)]
        self._round_robin_index[key] = start + 1
        return rotated

    @staticmethod
    def _cost(model: Model) -> float:
        """Estimated cost per 1k tokens; no fabricated pricing is introduced."""
        return (model.input_price_per_1k or 0.0) + (model.output_price_per_1k or 0.0)
