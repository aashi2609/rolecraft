"""Async Groq API client with retries and structured JSON output."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_GENERATE_URL = "https://api.groq.com/openai/v1/chat/completions"


class AIServiceError(Exception):
    """Raised when the Groq API call fails after retries."""


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
    """Call Groq chat completions and return the parsed JSON response.

    Falls back gracefully: after *retries* failures the last error is raised
    as an ``AIServiceError`` so callers can fall back to deterministic logic.
    """
    api_key = settings.groq_api_key
    if not api_key or not api_key.strip():
        logger.warning("GROQ_API_KEY is not configured or empty")
        raise AIServiceError("GROQ_API_KEY is not configured")

    used_model = model or settings.groq_model

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": used_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }

    # NOTE: We intentionally do NOT set response_format: json_object here.
    # Thinking models (e.g. Qwen 3.6) emit <think>...</think> blocks that
    # conflict with Groq's strict JSON validation, causing empty failures.
    # Instead, we rely on the prompt + system instruction to produce JSON
    # and extract it ourselves below.

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            timeout = 60.0 * attempt  # progressively longer timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug("Groq API call attempt %d/%d with model %s", attempt, retries, used_model)
                resp = await client.post(_GENERATE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                raise AIServiceError("Groq returned no choices")

            text = choices[0].get("message", {}).get("content", "")

            if not text or not text.strip():
                raise AIServiceError("Groq returned empty response")

            # Strip <think>...</think> blocks from thinking/reasoning models
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            # Strip markdown code fences
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]  # remove opening ```json
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # remove closing ```
                text = "\n".join(lines).strip()

            # Find the start of JSON object
            json_start = text.find("{")
            if json_start == -1:
                raise AIServiceError(f"No JSON object found in response: {text[:200]}")

            # Use raw_decode to parse just the first JSON object,
            # ignoring any trailing text/extra data
            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(text, json_start)
            logger.info("Groq API call successful on attempt %d", attempt)
            return parsed

        except json.JSONDecodeError as exc:
            last_error = AIServiceError(f"Failed to parse Groq JSON: {exc}")
            logger.warning("Groq JSON parse error (attempt %d/%d): %s — raw text: %.300s", attempt, retries, exc, text)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_text = exc.response.text[:200] if exc.response.text else "No error details"
            last_error = AIServiceError(f"Groq HTTP {status_code}: {error_text}")
            logger.warning("Groq HTTP error (attempt %d/%d): %s", attempt, retries, last_error)

            if status_code == 429 and attempt < retries:
                retry_after = exc.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = min(int(retry_after), 60)
                else:
                    wait = 2 ** attempt * 2
                logger.info("Rate limited. Waiting %ds before retry %d...", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            if 400 <= status_code < 500 and status_code != 429:
                logger.error("Client error %d, not retrying", status_code)
                break
        except httpx.TimeoutException as exc:
            last_error = AIServiceError(f"Groq timeout after {timeout}s: {exc}")
            logger.warning("Groq timeout (attempt %d/%d): %s", attempt, retries, exc)
        except Exception as exc:
            last_error = AIServiceError(f"Groq call failed: {exc}")
            logger.warning("Groq error (attempt %d/%d): %s", attempt, retries, exc)

    error_msg = f"Groq call failed after {retries} retries"
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
    """Call Groq and return raw text (no JSON parsing)."""
    api_key = settings.groq_api_key
    if not api_key or not api_key.strip():
        logger.warning("GROQ_API_KEY is not configured or empty")
        raise AIServiceError("GROQ_API_KEY is not configured")

    used_model = model or settings.groq_model

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": used_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(_GENERATE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise AIServiceError("Groq returned no choices")
    return choices[0]["message"]["content"]
