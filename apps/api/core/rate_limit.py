"""Central rate-limiting for abuse protection.

Storage backends (via RATE_LIMIT_STORAGE_URI):
  - memory://  — default; single-process only (same limitation as WebSocket manager)
  - redis://…  — shared store for multi-worker / multi-instance deploys

Client IP: X-Forwarded-For is honored ONLY when TRUSTED_PROXY=true.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from core.config import get_settings
from core.security import decode_access_token

logger = logging.getLogger(__name__)

# ── Tunable limits (single config location) ───────────────────────────────────
# Format: limits library strings ("N/minute", "N/hour").
RATE_LIMITS: dict[str, str] = {
    # Auth — IP buckets
    "signin_ip": "5/minute",
    "signup_ip": "5/hour",
    "forgot_password_ip": "10/hour",
    "reset_password_ip": "10/hour",  # future POST /auth/reset-password
    # Auth — identity buckets
    "signin_email_failed": "10/hour",
    "forgot_password_email": "3/hour",
    "reset_password_email": "3/hour",  # future POST /auth/reset-password
    "change_password_user": "5/hour",
    "delete_account_user": "5/hour",
    # Groq / expensive generation — burst on top of plan caps
    "groq_burst_user": "3/minute",
    # Messaging & uploads
    "messages_user": "30/minute",
    "uploads_user": "20/hour",
}

GENERIC_429_DETAIL = "Too many requests. Please try again later."


def get_client_ip(request: Request) -> str:
    """Return client IP; trust X-Forwarded-For only when TRUSTED_PROXY is set."""
    settings = get_settings()
    if settings.trusted_proxy:
        forwarded = request.headers.get("x-forwarded-for") or request.headers.get(
            "X-Forwarded-For"
        )
        if forwarded:
            # Left-most is the original client when proxies append.
            return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_user_key(request: Request) -> str:
    """Rate-limit key from Bearer JWT sub, else fall back to client IP."""
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return f"ip:{get_client_ip(request)}"


def _make_storage_and_strategy():
    settings = get_settings()
    storage = storage_from_string(settings.rate_limit_storage_uri)
    strategy = MovingWindowRateLimiter(storage)
    return storage, strategy, settings


_storage, _strategy, _settings_snapshot = _make_storage_and_strategy()

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=_settings_snapshot.rate_limit_storage_uri,
    enabled=_settings_snapshot.rate_limit_enabled,
    headers_enabled=True,
    swallow_errors=False,
)

logger.info(
    "Rate limit backend ready: storage=%s enabled=%s trusted_proxy=%s",
    _settings_snapshot.rate_limit_storage_uri,
    _settings_snapshot.rate_limit_enabled,
    _settings_snapshot.trusted_proxy,
)


def reset_rate_limit_backends() -> None:
    """Rebuild limiter/strategy after settings changes (tests)."""
    global _storage, _strategy, _settings_snapshot, limiter
    _storage, _strategy, _settings_snapshot = _make_storage_and_strategy()
    limiter = Limiter(
        key_func=get_client_ip,
        storage_uri=_settings_snapshot.rate_limit_storage_uri,
        enabled=_settings_snapshot.rate_limit_enabled,
        headers_enabled=True,
        swallow_errors=False,
    )


def _retry_after_seconds(limit_str: str, *key_parts: str) -> int:
    item = parse(limit_str)
    stats = _strategy.get_window_stats(item, *key_parts)
    reset_at = getattr(stats, "reset_time", None)
    if reset_at is None:
        return 60
    return max(1, int(reset_at - time.time()))


def hit_limit(limit_key: str, *identity_parts: str) -> tuple[bool, int]:
    """Consume one hit. Returns (allowed, retry_after_seconds)."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return True, 0
    limit_str = RATE_LIMITS[limit_key]
    item = parse(limit_str)
    namespace = ("rolecraft", limit_key, *identity_parts)
    allowed = _strategy.hit(item, *namespace)
    if allowed:
        return True, 0
    return False, _retry_after_seconds(limit_str, *namespace)


def enforce_limit(limit_key: str, *identity_parts: str) -> None:
    """Raise RateLimited if this identity is over the named limit."""
    allowed, retry_after = hit_limit(limit_key, *identity_parts)
    if not allowed:
        raise RateLimited(retry_after=retry_after)


def enforce_reset_password_limits(request: Request, email: str) -> None:
    """Call from future POST /auth/reset-password (email bucket).

    Pair with ``@limiter.limit(RATE_LIMITS["reset_password_ip"])`` on the route
    for the per-IP cap. Same policy as forgot-password: 3/hour email, 10/hour IP.
    """
    email_key = (email or "").strip().lower() or "unknown"
    enforce_limit("reset_password_email", email_key)


class RateLimited(Exception):
    """Raised when a custom (non-slowapi-decorator) limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = max(1, int(retry_after))
        super().__init__(GENERIC_429_DETAIL)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Unified 429 handler — generic body, Retry-After header, no email leakage."""
    retry_after = 60
    if isinstance(exc, RateLimited):
        retry_after = exc.retry_after
    elif isinstance(exc, RateLimitExceeded):
        # Prefer slowapi window stats when available on the request
        view_limit = getattr(request.state, "view_rate_limit", None)
        if view_limit is not None:
            try:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": GENERIC_429_DETAIL},
                )
                return limiter._inject_headers(response, view_limit)
            except Exception:
                pass
        detail = getattr(exc, "detail", None)
        if detail is not None and hasattr(detail, "get_expiry"):
            try:
                retry_after = max(1, int(detail.get_expiry() or 60))
            except Exception:
                retry_after = 60
    return JSONResponse(
        status_code=429,
        content={"detail": GENERIC_429_DETAIL},
        headers={"Retry-After": str(retry_after)},
    )
