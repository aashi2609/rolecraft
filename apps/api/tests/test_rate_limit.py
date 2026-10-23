"""Unit tests for rate-limit helpers (no Neon / TestClient required)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.rate_limit import (
    RATE_LIMITS,
    GENERIC_429_DETAIL,
    RateLimited,
    enforce_limit,
    get_client_ip,
    hit_limit,
    rate_limit_exceeded_handler,
    reset_rate_limit_backends,
)
from core.config import get_settings


@pytest.fixture(autouse=True)
def _memory_limits(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("TRUSTED_PROXY", "false")
    get_settings.cache_clear()
    reset_rate_limit_backends()
    yield
    get_settings.cache_clear()
    reset_rate_limit_backends()


def test_rate_limits_config_has_required_keys():
    required = {
        "signin_ip",
        "signin_email_failed",
        "signup_ip",
        "forgot_password_ip",
        "forgot_password_email",
        "reset_password_ip",
        "reset_password_email",
        "change_password_user",
        "delete_account_user",
        "groq_burst_user",
        "messages_user",
        "uploads_user",
    }
    assert required <= set(RATE_LIMITS.keys())


def test_get_client_ip_ignores_xff_without_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "false")
    get_settings.cache_clear()
    reset_rate_limit_backends()

    request = MagicMock()
    request.headers = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    request.client.host = "127.0.0.1"
    assert get_client_ip(request) == "127.0.0.1"


def test_get_client_ip_uses_xff_when_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "true")
    get_settings.cache_clear()
    reset_rate_limit_backends()

    request = MagicMock()
    request.headers = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    request.client.host = "127.0.0.1"
    assert get_client_ip(request) == "203.0.113.9"


def test_hit_limit_blocks_after_budget():
    # Use a dedicated key so we don't collide with other tests
    key = "signup_ip"
    # Burn the budget (5/hour)
    for i in range(5):
        allowed, _ = hit_limit(key, "test-ip-budget")
        assert allowed, f"hit {i+1} should be allowed"

    allowed, retry = hit_limit(key, "test-ip-budget")
    assert allowed is False
    assert retry >= 1

    # Different identity is unaffected
    allowed2, _ = hit_limit(key, "other-ip-budget")
    assert allowed2 is True


def test_enforce_limit_raises_rate_limited():
    for _ in range(5):
        enforce_limit("signup_ip", "enforce-ip")
    with pytest.raises(RateLimited) as ei:
        enforce_limit("signup_ip", "enforce-ip")
    assert ei.value.retry_after >= 1


def test_429_handler_is_generic_with_retry_after():
    request = MagicMock()
    resp = rate_limit_exceeded_handler(request, RateLimited(retry_after=42))
    assert resp.status_code == 429
    assert resp.body
    import json

    body = json.loads(resp.body.decode())
    assert body["detail"] == GENERIC_429_DETAIL
    assert "exists" not in body["detail"].lower()
    assert resp.headers["Retry-After"] == "42"
