"""OpenAI-compatible embeddings client: batch calls, bounded retries, no placeholders."""

from __future__ import annotations

import asyncio
import logging
import random
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
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0
TOTAL_TIMEOUT = 90.0
MAX_RETRIES = 3
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class EmbeddingServiceError(Exception):
    """Raised when an embeddings API call fails after retries."""


_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(TOTAL_TIMEOUT, connect=CONNECT_TIMEOUT, read=READ_TIMEOUT)
        )
    return _client


async def aclose_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
    return min(2.0**attempt + random.uniform(0, 1.0), 30.0)


async def fetch_embeddings(
    texts: list[str], *, model: str | None = None, retries: int = MAX_RETRIES
) -> list[list[float]]:
    """Return one vector per input text, in order, or raise EmbeddingServiceError.

    Retries only 429/5xx and network errors with exponential backoff + jitter,
    honoring Retry-After. Never retries other 4xx. Never returns placeholders.
    """
    if not texts:
        return []
    payload_texts = [(t or "").strip()[:MAX_INPUT_CHARS] for t in texts]
    if any(not t for t in payload_texts):
        raise EmbeddingServiceError("Empty text for embedding")

    url = f"{settings.embedding_api_base.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.embedding_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or settings.embedding_model,
        "input": payload_texts,
    }

    client = _get_client()
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = await client.post(url, headers=headers, json=body)
            if response.status_code in _RETRYABLE_STATUS:
                last_error = EmbeddingServiceError(f"Embedding API HTTP {response.status_code}")
                if attempt < retries - 1:
                    await asyncio.sleep(_retry_delay(response, attempt + 1))
                    continue
                raise last_error
            response.raise_for_status()
            return _parse_embeddings_response(response.json(), len(payload_texts))
        except httpx.HTTPStatusError as exc:
            # Non-retryable 4xx (400/401/403): fail immediately.
            last_error = exc
            raise EmbeddingServiceError(f"Embedding API HTTP {exc.response.status_code}") from exc
        except (httpx.TransportError, asyncio.TimeoutError) as exc:
            last_error = exc
            if attempt < retries - 1:
                await asyncio.sleep(_retry_delay(None, attempt + 1))
                continue
            raise EmbeddingServiceError(f"Embedding API network error: {exc}") from exc
        except EmbeddingServiceError:
            raise
        except Exception as exc:  # malformed JSON etc. — not retryable
            raise EmbeddingServiceError(f"Embedding API error: {exc}") from exc

    raise EmbeddingServiceError(str(last_error or "embedding request failed"))


async def fetch_embedding(text: str, **kwargs: Any) -> list[float]:
    """Single-text convenience wrapper around fetch_embeddings."""
    vectors = await fetch_embeddings([text], **kwargs)
    return vectors[0]


def _parse_embeddings_response(data: dict[str, Any], expected: int) -> list[list[float]]:
    items = data.get("data")
    if not isinstance(items, list) or len(items) != expected:
        raise EmbeddingServiceError(
            f"Embedding response count mismatch: expected {expected}, "
            f"got {len(items) if isinstance(items, list) else 'none'}"
        )
    # OpenAI returns items keyed by 'index'; sort to preserve input order.
    items = sorted(items, key=lambda it: it.get("index", 0))
    vectors: list[list[float]] = []
    for item in items:
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise EmbeddingServiceError("Embedding response missing vector")
        vectors.append([float(x) for x in embedding])
    return vectors
