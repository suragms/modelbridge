from __future__ import annotations

import random
from dataclasses import dataclass

from app.models.model import Model
from app.models.provider import Provider, ProviderStatus


@dataclass
class CandidateModel:
    model: Model
    provider: Provider
    score: float = 0.0
    latency_ms: float = 0.0


@dataclass
class RouteDecision:
    model: Model
    provider: Provider
    strategy: str
    fallback_used: bool = False
    candidates_evaluated: int = 0


class RoutingEngine:
    def __init__(self):
        self._latency_cache: dict[str, list[float]] = {}

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
            return 1000.0
        return sum(cache) / len(cache)

    def route(
        self,
        models: list[Model],
        providers: list[Provider],
        strategy: str = "auto",
        policy_config: dict | None = None,
    ) -> RouteDecision | None:
        candidates = self._build_candidates(models, providers)
        if not candidates:
            return None

        strategy_fn = self._get_strategy(strategy)
        scored = strategy_fn(candidates, policy_config or {})

        if not scored:
            return None

        best = scored[0]
        return RouteDecision(
            model=best.model,
            provider=best.provider,
            strategy=strategy,
            candidates_evaluated=len(candidates),
        )

    def _build_candidates(self, models: list[Model], providers: list[Provider]) -> list[CandidateModel]:
        provider_map = {str(p.id): p for p in providers}
        candidates = []
        for model in models:
            if not model.is_enabled:
                continue
            provider = provider_map.get(str(model.provider_id))
            if not provider or not provider.is_enabled or provider.status == ProviderStatus.OFFLINE:
                continue
            candidates.append(CandidateModel(model=model, provider=provider))
        return candidates

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
        }
        return strategies.get(strategy, self._strategy_balanced)

    def _strategy_balanced(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        quality_weight = config.get("quality_weight", 0.35)
        speed_weight = config.get("speed_weight", 0.30)
        cost_weight = config.get("cost_weight", 0.20)
        reliability_weight = config.get("reliability_weight", 0.15)

        for c in candidates:
            latency = self.get_avg_latency(str(c.model.id))
            speed_score = max(0, 1 - (latency / 5000))
            cost_score = max(0, 1 - (c.model.input_price_per_1k * 100))
            reliability_score = 1.0 if c.provider.status == "healthy" else 0.5

            c.score = (
                quality_weight * c.model.quality_score
                + speed_weight * speed_score
                + cost_weight * cost_score
                + reliability_weight * reliability_score
            )

        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_priority(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        priority_order = config.get("priority_model_ids", [])
        priority_map = {mid: i for i, mid in enumerate(priority_order)}
        for c in candidates:
            c.score = -priority_map.get(str(c.model.id), len(priority_order))
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_cheapest(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        for c in candidates:
            c.score = -(c.model.input_price_per_1k + c.model.output_price_per_1k)
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_fastest(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        for c in candidates:
            latency = self.get_avg_latency(str(c.model.id))
            c.score = -latency
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_quality(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        for c in candidates:
            c.score = c.model.quality_score
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_local(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        local_types = {"ollama", "lmstudio"}
        for c in candidates:
            c.score = 1.0 if c.provider.type in local_types else -1.0
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_privacy(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        local_types = {"ollama", "lmstudio"}
        trusted = config.get("trusted_providers", [])
        for c in candidates:
            if c.provider.type in local_types:
                c.score = 2.0
            elif c.provider.name in trusted:
                c.score = 1.0
            else:
                c.score = 0.0
        return sorted(candidates, key=lambda x: x.score, reverse=True)

    def _strategy_round_robin(
        self, candidates: list[CandidateModel], config: dict
    ) -> list[CandidateModel]:
        return random.sample(candidates, len(candidates))
