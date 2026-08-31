"""Provider-agnostic content safety interface.

The built-in backend is a local keyword heuristic. It is not a comprehensive
moderation system and is not a substitute for a dedicated safety provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SafetyVerdict:
    allowed: bool
    categories: list[str]
    reason: str
    backend: str


class ContentSafetyBackend(Protocol):
    name: str

    def evaluate(self, text: str) -> SafetyVerdict: ...


class HeuristicSafetyBackend:
    name = "heuristic_local"

    _KEYWORDS = {
        "violence": ("build a bomb", "how to kill"),
        "self_harm": ("suicide methods",),
        "exploitation": ("child sexual",),
    }

    def evaluate(self, text: str) -> SafetyVerdict:
        lowered = text.lower()
        hits: list[str] = []
        for category, phrases in self._KEYWORDS.items():
            if any(p in lowered for p in phrases):
                hits.append(category)
        if hits:
            return SafetyVerdict(
                allowed=False,
                categories=hits,
                reason="Heuristic safety keywords matched",
                backend=self.name,
            )
        return SafetyVerdict(allowed=True, categories=[], reason="No heuristic matches", backend=self.name)


def get_safety_backend() -> ContentSafetyBackend:
    return HeuristicSafetyBackend()
