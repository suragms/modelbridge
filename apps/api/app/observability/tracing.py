"""OpenTelemetry-ready tracing abstraction.

Full OpenTelemetry export is not wired by default. Configure an OTLP exporter
and replace NoOpTracer with an OTel-backed implementation when ready.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from enum import StrEnum
from typing import Any


class SpanKind(StrEnum):
    SERVER = "server"
    CLIENT = "client"
    INTERNAL = "internal"


class Span:
    def __init__(self, name: str, kind: SpanKind = SpanKind.INTERNAL) -> None:
        self.name = name
        self.kind = kind
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        pass


class Tracer:
    """Minimal tracer interface compatible with future OpenTelemetry wiring."""

    @contextmanager
    def start_span(
        self, name: str, kind: SpanKind = SpanKind.INTERNAL
    ) -> Generator[Span, None, None]:
        span = Span(name, kind)
        try:
            yield span
        finally:
            span.end()


_tracer = Tracer()


def get_tracer() -> Tracer:
    return _tracer
