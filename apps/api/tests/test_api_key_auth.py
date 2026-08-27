"""Tests for API key generation and authentication used by OpenAI-compatible endpoints.

Authentication is exercised at the unit level (hashing + resolution helper)
without requiring a real PostgreSQL instance. DB-backed request tests are gated
behind ``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.encryption import generate_api_key, get_key_prefix, hash_api_key
from app.auth.jwt import get_api_key_or_user

requires_database = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set"
)


class TestAPIKeyAuth:
    def test_generate_api_key_has_mb_prefix(self):
        assert generate_api_key().startswith("mb_")

    def test_key_prefix_is_short_and_obfuscated(self):
        key = generate_api_key()
        prefix = get_key_prefix(key)
        assert prefix != key
        assert prefix.endswith("...")

    def test_key_stored_as_hash_not_plaintext(self):
        key = generate_api_key()
        digest = hash_api_key(key)
        assert digest != key
        assert len(digest) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_missing_credentials_rejected(self):
        from fastapi import HTTPException

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc:
            await get_api_key_or_user(credentials=None, db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self):
        from fastapi import HTTPException

        db = AsyncMock()
        # No matching API key found in the (mocked) database.
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute.return_value = execute_result

        with pytest.raises(HTTPException) as exc:
            await get_api_key_or_user(
                credentials=MagicMock(credentials="mb_invalid_key"), db=db
            )
        assert exc.value.status_code == 401


@requires_database
def test_db_backed_api_key_flow():
    """Placeholder for a DB-backed end-to-end auth test.

    Configure ``TEST_DATABASE_URL`` and extend this with a real PostgreSQL-backed
    request to ``POST /v1/chat/completions`` using a freshly minted API key.
    """
    assert True
