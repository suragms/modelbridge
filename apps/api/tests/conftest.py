"""Pytest configuration and shared fixtures for the ModelBridge API test suite.

Most tests are pure unit tests or use mocked HTTP clients and therefore do not
require PostgreSQL, Redis, or a running Ollama server.

DB-backed HTTP endpoint tests are gated behind ``TEST_DATABASE_URL`` and skip
automatically when it is not configured.
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def event_loop():
    """Provide a fresh asyncio loop for pytest-asyncio (safer on Windows)."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
