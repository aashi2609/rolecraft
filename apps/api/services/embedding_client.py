"""OpenAI-compatible embedding API client with mock fallback."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import get_settings

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_INPUT_CHARS = 8000


class EmbeddingServiceError(Exception):
    """Raised when embedding API call fails after retries."""


async def fetch_embedding(text: str, *, retries: int = 3) -> list[float]:
    """Return a 1536-dim vector from the configured provider, or raise."""
    payload_text = (text or "").strip()[:MAX_INPUT_CHARS]
    if not payload_text:
        raise EmbeddingServiceError("Empty text for embedding")

    url = f"{settings.embedding_api_base.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.embedding_api_key}",
        "Content-Type": "application/json",
    }
    body = {"model": settings.embedding_model, "input": payload_text}

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            vector = _parse_embedding_response(data)
            if len(vector) != 1536:
                raise EmbeddingServiceError(f"Expected 1536 dims, got {len(vector)}")
            return vector
        except Exception as exc:
            last_error = exc
            logger.warning("Embedding API attempt %s failed: %s", attempt + 1, exc)

    raise EmbeddingServiceError(str(last_error or "embedding request failed"))


def _parse_embedding_response(data: dict[str, Any]) -> list[float]:
    items = data.get("data")
    if not items:
        raise EmbeddingServiceError("Embedding response missing data")
    embedding = items[0].get("embedding")
    if not isinstance(embedding, list):
        raise EmbeddingServiceError("Embedding response missing vector")
    return [float(x) for x in embedding]
