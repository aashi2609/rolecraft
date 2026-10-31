"""Unit tests for embedding_service and embedding_client."""

from __future__ import annotations

import pytest
pytestmark = pytest.mark.skip_db_guard

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.embedding_client import EmbeddingServiceError, fetch_embedding
from services.embedding_service import embed_text, EmbeddingError


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

    fake_vector = [0.1] * 512  # text-embedding-3-small is 512-dim
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {"data": [{"embedding": fake_vector}]}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

    with patch("services.embedding_client.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(fetch_embedding("backend engineer"))

    assert result == fake_vector
    assert len(result) == 512  # Verify correct dimension


def test_fetch_embedding_raises_on_empty_data(monkeypatch) -> None:
    import services.embedding_client as ec

    monkeypatch.setattr(ec.settings, "embedding_api_key", "test-key")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {"data": []}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

    with patch("services.embedding_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(EmbeddingServiceError):
            asyncio.run(fetch_embedding("test"))
