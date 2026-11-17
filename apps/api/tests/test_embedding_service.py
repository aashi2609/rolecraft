"""Unit tests for embedding_service and embedding_client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.embedding_client import EmbeddingServiceError, fetch_embedding
from services.embedding_service import EmbeddingError


def _embedding_response(payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    return httpx.Response(200, json=payload, request=request)


pytestmark = pytest.mark.skip_db_guard


def test_embed_text_requires_api_key() -> None:
    """When API key is empty, embed_text raises EmbeddingError."""
    import services.embedding_service as es

    with patch.object(es.settings, "embedding_api_key", ""):
        with pytest.raises(EmbeddingError) as exc_info:
            asyncio.run(es.embed_text("software engineer python"))

        assert "key not configured" in str(exc_info.value).lower()


def test_fetch_embedding_parses_openai_response(monkeypatch) -> None:
    import services.embedding_client as ec

    monkeypatch.setattr(ec.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(ec.settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr(ec.settings, "embedding_api_base", "https://api.openai.com/v1")

    fake_vector = [0.1] * 512
    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.post = AsyncMock(
        return_value=_embedding_response({"data": [{"index": 0, "embedding": fake_vector}]})
    )

    with patch("services.embedding_client._get_client", return_value=mock_client):
        result = asyncio.run(fetch_embedding("backend engineer"))

    assert result == fake_vector
    assert len(result) == 512  # Verify correct dimension


def test_fetch_embedding_raises_on_empty_data(monkeypatch) -> None:
    import services.embedding_client as ec

    monkeypatch.setattr(ec.settings, "embedding_api_key", "test-key")

    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.post = AsyncMock(return_value=_embedding_response({"data": []}))

    with patch("services.embedding_client._get_client", return_value=mock_client):
        with pytest.raises(EmbeddingServiceError):
            asyncio.run(fetch_embedding("test"))
