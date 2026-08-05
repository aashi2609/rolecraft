"""Async Gemini API client with retries and structured JSON output."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


class AIServiceError(Exception):
    """Raised when the Gemini API call fails after retries."""


async def generate_content(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
    response_mime_type: str = "application/json",
    retries: int = 3,
) -> dict[str, Any]:
    """Call Gemini generateContent and return the parsed JSON response.

    Falls back gracefully: after *retries* failures the last error is raised
    as an ``AIServiceError`` so callers can fall back to deterministic logic.
    """
    api_key = settings.gemini_api_key
    if not api_key or not api_key.strip():
        logger.warning("GEMINI_API_KEY is not configured or empty")
        raise AIServiceError("GEMINI_API_KEY is not configured")

    used_model = model or settings.gemini_model
    url = _GENERATE_URL.format(model=used_model, key=api_key)

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": response_mime_type,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            timeout = 60.0 * attempt  # progressively longer timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug("Gemini API call attempt %d/%d with model %s", attempt, retries, used_model)
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Extract text from the response
            candidates = data.get("candidates", [])
            if not candidates:
                raise AIServiceError("Gemini returned no candidates")

            # Check for safety filters or block reasons
            if "finishReason" in candidates[0]:
                finish_reason = candidates[0]["finishReason"]
                if finish_reason in ["SAFETY", "RECITATION", "BLOCKED"]:
                    raise AIServiceError(f"Gemini blocked content: {finish_reason}")

            text = candidates[0]["content"]["parts"][0]["text"]

            if not text or not text.strip():
                raise AIServiceError("Gemini returned empty response")

            # Parse JSON from response text
            # Gemini sometimes wraps JSON in ```json ... ``` blocks
            text = text.strip()
            if text.startswith("```"):
                # Strip markdown code fence
                lines = text.split("\n")
                lines = lines[1:]  # remove opening ```json
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # remove closing ```
                text = "\n".join(lines)

            parsed = json.loads(text)
            logger.info("Gemini API call successful on attempt %d", attempt)
            return parsed

        except json.JSONDecodeError as exc:
            last_error = AIServiceError(f"Failed to parse Gemini JSON: {exc}")
            logger.warning("Gemini JSON parse error (attempt %d/%d): %s", attempt, retries, exc)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_text = exc.response.text[:200] if exc.response.text else "No error details"
            last_error = AIServiceError(f"Gemini HTTP {status_code}: {error_text}")
            logger.warning("Gemini HTTP error (attempt %d/%d): %s", attempt, retries, last_error)

            # Exponential backoff for rate-limit (429) errors
            if status_code == 429 and attempt < retries:
                # Check for Retry-After header, otherwise use exponential backoff
                retry_after = exc.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = min(int(retry_after), 60)
                else:
                    wait = 2 ** attempt * 2  # 4s, 8s, 16s
                logger.info("Rate limited. Waiting %ds before retry %d...", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            # Don't retry on client errors (4xx except 429)
            if 400 <= status_code < 500 and status_code != 429:
                logger.error("Client error %d, not retrying", status_code)
                break
        except httpx.TimeoutException as exc:
            last_error = AIServiceError(f"Gemini timeout after {timeout}s: {exc}")
            logger.warning("Gemini timeout (attempt %d/%d): %s", attempt, retries, exc)
        except Exception as exc:
            last_error = AIServiceError(f"Gemini call failed: {exc}")
            logger.warning("Gemini error (attempt %d/%d): %s", attempt, retries, exc)

    error_msg = f"Gemini call failed after {retries} retries"
    if last_error:
        error_msg += f": {last_error}"
    raise last_error or AIServiceError(error_msg)


async def generate_text(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
) -> str:
    """Call Gemini and return raw text (no JSON parsing)."""
    api_key = settings.gemini_api_key
    if not api_key or not api_key.strip():
        logger.warning("GEMINI_API_KEY is not configured or empty")
        raise AIServiceError("GEMINI_API_KEY is not configured")

    used_model = model or settings.gemini_model
    url = _GENERATE_URL.format(model=used_model, key=api_key)

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise AIServiceError("Gemini returned no candidates")
    return candidates[0]["content"]["parts"][0]["text"]
