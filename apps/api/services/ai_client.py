"""Async Groq API client with retries, circuit breaker, and structured JSON output."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from typing import Any

import httpx

from core.config import get_settings

# Windows / corporate proxies often lack a usable CA bundle for httpx.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

logger = logging.getLogger(__name__)

settings = get_settings()

_GENERATE_URL = "https://api.groq.com/openai/v1/chat/completions"


class AIServiceError(Exception):
    """Raised when the Groq API call fails after retries."""
    
    def __init__(self, message: str, error_code: str = "ai_unavailable", retry_after: int | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after


class CircuitBreakerState:
    """Circuit breaker to protect against hammering a down provider."""
    
    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False
        self.open_at = 0.0
        self.consecutive_successes = 0
    
    def record_success(self):
        """Reset failure count on successful call."""
        self.failure_count = 0
        self.consecutive_successes += 1
        if self.is_open and self.consecutive_successes >= 2:
            # Close circuit after 2 consecutive successes
            logger.info("Circuit breaker closed after 2 successful calls")
            self.is_open = False
    
    def record_failure(self):
        """Increment failure count and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.consecutive_successes = 0
        
        # Open circuit after 5 consecutive failures
        if self.failure_count >= 5:
            self.is_open = True
            self.open_at = time.time()
            logger.error(
                "Circuit breaker opened: %d consecutive failures. Cooldown: 30s",
                self.failure_count
            )
    
    def check_and_reset(self, cooldown_seconds: int = 30) -> bool:
        """Check if circuit breaker should block the call.
        
        Returns True if call should proceed, False if blocked.
        """
        if not self.is_open:
            return True
        
        elapsed = time.time() - self.open_at
        if elapsed >= cooldown_seconds:
            # Allow one retry attempt after cooldown
            logger.info("Circuit breaker: cooldown expired, allowing retry")
            self.is_open = False
            self.failure_count = 0
            return True
        
        return False


# Global circuit breaker instance
_circuit_breaker = CircuitBreakerState()


def _calculate_backoff_with_jitter(attempt: int, retry_after: int | None = None) -> float:
    """Calculate backoff duration with jitter to prevent thundering herd.
    
    Args:
        attempt: Current retry attempt (1-indexed)
        retry_after: Retry-After header value in seconds (if provided)
    
    Returns:
        Sleep duration in seconds
    """
    if retry_after:
        # Respect Retry-After but cap at 300s
        base_wait = min(retry_after, 300)
    else:
        # Exponential backoff: 4s, 8s, 16s for attempts 1, 2, 3
        base_wait = 2 ** attempt * 2
    
    # Add jitter: ±10%
    jitter_factor = random.uniform(0.9, 1.1)
    
    return base_wait * jitter_factor


def _extract_message_text(message: dict[str, Any]) -> str:
    """Return assistant text from Groq message (content or reasoning fallback)."""
    content = (message.get("content") or "").strip()
    if content:
        return content

    reasoning = (message.get("reasoning") or "").strip()
    if reasoning:
        return reasoning

    return ""


def _parse_json_response(text: str) -> dict[str, Any]:
    """Strip fences / thinking blocks and parse the first JSON object."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    json_start = text.find("{")
    if json_start == -1:
        raise AIServiceError(
            f"No JSON object found in response: {text[:200]}", 
            error_code="ai_bad_output"
        )

    decoder = json.JSONDecoder()
    parsed, _ = decoder.raw_decode(text, json_start)
    if not isinstance(parsed, dict):
        raise AIServiceError(
            "Groq response JSON root must be an object",
            error_code="ai_bad_output"
        )
    return parsed


async def generate_content(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
    response_mime_type: str = "application/json",
    retries: int = 3,
    deadline_seconds: int = 300,
) -> dict[str, Any]:
    """Call Groq chat completions and return the parsed JSON response.
    
    Features:
    - Circuit breaker: Opens after 5 consecutive failures, 30s cooldown
    - Request deadline: Hard cap on total time (default 300s)
    - Exponential backoff with jitter: Prevents thundering herd
    - Retry-After respect: Honors rate limit headers up to 300s
    - Error classification: Only retries transient errors (timeout, 429, 5xx)
    
    Args:
        prompt: User prompt text
        system_instruction: Optional system prompt
        model: Model name (default from settings)
        temperature: Sampling temperature
        max_output_tokens: Max tokens in response
        response_mime_type: Response format (default: application/json)
        retries: Max retry attempts (default: 3)
        deadline_seconds: Total time limit for all retries (default: 300s)
    
    Returns:
        Parsed JSON response as dict
    
    Raises:
        AIServiceError: With error_code and optional retry_after
    """
    # Check circuit breaker first
    if not _circuit_breaker.check_and_reset(cooldown_seconds=30):
        time_until_reset = 30 - (time.time() - _circuit_breaker.open_at)
        raise AIServiceError(
            f"AI service temporarily unavailable (circuit breaker open). Retry in {int(time_until_reset)}s.",
            error_code="ai_unavailable",
            retry_after=int(time_until_reset)
        )
    
    api_key = settings.groq_api_key
    if not api_key or not api_key.strip():
        logger.error("GROQ_API_KEY is not configured or empty")
        raise AIServiceError(
            "GROQ_API_KEY is not configured",
            error_code="ai_auth_failed"
        )

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
    # Thinking models emit reasoning blocks that conflict with strict JSON mode.
    # We rely on the prompt + system instruction and parse JSON ourselves.

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start_time = time.time()
    deadline = start_time + deadline_seconds
    
    last_error: Exception | None = None
    text = ""
    
    for attempt in range(1, retries + 1):
        # Check deadline
        elapsed = time.time() - start_time
        time_remaining = deadline - time.time()
        
        if time_remaining <= 0:
            logger.error(
                "Request exceeded %ds deadline after %d retries (%.1fs elapsed)",
                deadline_seconds,
                attempt - 1,
                elapsed
            )
            raise AIServiceError(
                f"Request exceeded {deadline_seconds}s deadline after {attempt - 1} retries",
                error_code="ai_timeout"
            )
        
        # Cap per-attempt timeout to remaining time (with 5s buffer for cleanup)
        attempt_timeout = min(60.0 * attempt, time_remaining - 5)
        attempt_timeout = max(attempt_timeout, 10.0)  # At least 10s per attempt
        
        try:
            async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                logger.debug(
                    "Groq API call attempt %d/%d with model %s (timeout: %.1fs, deadline: %.1fs remaining)",
                    attempt,
                    retries,
                    used_model,
                    attempt_timeout,
                    time_remaining
                )
                resp = await client.post(_GENERATE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                raise AIServiceError("Groq returned no choices", error_code="ai_bad_output")

            message = choices[0].get("message", {})
            text = _extract_message_text(message)

            if not text:
                raise AIServiceError("Groq returned empty response", error_code="ai_bad_output")

            parsed = _parse_json_response(text)
            
            # Success! Record and return
            _circuit_breaker.record_success()
            logger.info(
                "Groq API call successful on attempt %d (%.1fs elapsed)",
                attempt,
                time.time() - start_time
            )
            return parsed

        except json.JSONDecodeError as exc:
            last_error = AIServiceError(
                f"Failed to parse Groq JSON: {exc}",
                error_code="ai_bad_output"
            )
            logger.warning(
                "Groq JSON parse error (attempt %d/%d): %s — raw text: %.300s",
                attempt,
                retries,
                exc,
                text,
            )
            _circuit_breaker.record_failure()
            
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_text = (
                exc.response.text[:200] if exc.response.text else "No error details"
            )
            
            # 401/403: Auth failures - don't retry
            if status_code in (401, 403):
                logger.error(
                    "Groq authentication failed (HTTP %d): %s. Check GROQ_API_KEY.",
                    status_code,
                    error_text
                )
                _circuit_breaker.record_failure()
                raise AIServiceError(
                    "AI service authentication failed",
                    error_code="ai_auth_failed"
                )
            
            # 429: Rate limit - respect Retry-After
            if status_code == 429:
                retry_after_header = exc.response.headers.get("Retry-After")
                if retry_after_header and retry_after_header.isdigit():
                    retry_after_int = int(retry_after_header)
                else:
                    retry_after_int = None
                
                last_error = AIServiceError(
                    f"Groq rate limited: {error_text}",
                    error_code="ai_rate_limited",
                    retry_after=retry_after_int
                )
                
                if attempt < retries:
                    wait = _calculate_backoff_with_jitter(attempt, retry_after_int)
                    logger.info(
                        "Rate limited (HTTP 429). Waiting %.1fs before retry %d...",
                        wait,
                        attempt + 1
                    )
                    await asyncio.sleep(wait)
                    continue
                else:
                    _circuit_breaker.record_failure()
                    raise last_error
            
            # 400: Client error (context length, malformed request) - don't retry
            if 400 <= status_code < 500:
                logger.error(
                    "Groq client error %d (attempt %d/%d): %s. Not retrying.",
                    status_code,
                    attempt,
                    retries,
                    error_text
                )
                _circuit_breaker.record_failure()
                raise AIServiceError(
                    f"AI service rejected request: {error_text[:100]}",
                    error_code="ai_bad_output"
                )
            
            # 5xx: Server error - retry with backoff
            last_error = AIServiceError(f"Groq HTTP {status_code}: {error_text}", error_code="ai_unavailable")
            logger.warning(
                "Groq server error (attempt %d/%d): HTTP %d",
                attempt,
                retries,
                status_code
            )
            _circuit_breaker.record_failure()
            
        except httpx.TimeoutException as exc:
            last_error = AIServiceError(
                f"Groq timeout after {attempt_timeout:.1f}s: {exc}",
                error_code="ai_timeout"
            )
            logger.warning(
                "Groq timeout (attempt %d/%d, %.1fs timeout)",
                attempt,
                retries,
                attempt_timeout
            )
            _circuit_breaker.record_failure()
            
        except AIServiceError as exc:
            last_error = exc
            logger.warning("Groq error (attempt %d/%d): %s", attempt, retries, exc)
            _circuit_breaker.record_failure()
            
        except Exception as exc:
            last_error = AIServiceError(f"Groq call failed: {exc}", error_code="ai_unavailable")
            logger.warning(
                "Groq unexpected error (attempt %d/%d): %s",
                attempt,
                retries,
                exc
            )
            _circuit_breaker.record_failure()
        
        # Exponential backoff with jitter (for non-429 errors)
        if attempt < retries and last_error and last_error.error_code != "ai_rate_limited":
            wait = _calculate_backoff_with_jitter(attempt)
            logger.info("Waiting %.1fs before retry %d...", wait, attempt + 1)
            await asyncio.sleep(wait)

    # All retries exhausted
    error_msg = f"Groq call failed after {retries} retries (deadline: {deadline_seconds}s)"
    if last_error:
        error_msg += f": {last_error}"
    
    logger.error("%s (%.1fs total)", error_msg, time.time() - start_time)
    raise last_error or AIServiceError(error_msg, error_code="ai_unavailable")
