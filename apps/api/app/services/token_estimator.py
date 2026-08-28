"""Extensible token estimation interface.

Different models may require different tokenizers. This module provides a
pluggable estimator without claiming universal accuracy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TokenEstimator(ABC):
    @abstractmethod
    def estimate(self, text: str) -> int:
        """Return estimated token count for the given text."""


class CharacterBasedEstimator(TokenEstimator):
    """Rough heuristic: ~4 characters per token for English-like text.

    This is intentionally labeled as ESTIMATED — not exact.
    """

    def __init__(self, chars_per_token: float = 4.0) -> None:
        self.chars_per_token = chars_per_token

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / self.chars_per_token))


_default_estimator = CharacterBasedEstimator()


def get_token_estimator() -> TokenEstimator:
    return _default_estimator


def estimate_message_tokens(messages: list[dict]) -> tuple[int, int]:
    """Estimate input/output tokens from chat messages when provider usage is unavailable."""
    estimator = get_token_estimator()
    input_tokens = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    input_tokens += estimator.estimate(str(part.get("text", "")))
        else:
            input_tokens += estimator.estimate(str(content))
    return input_tokens, 0
