"""Tests for 2B: Production Error Responses.

Verifies:
1. In production, unhandled exceptions return 500 with {"detail": "Internal server error", "request_id": "..."}.
2. Database errors (IntegrityError, etc.) map to clean 409/400 without leaking SQL or constraint names.
3. RequestValidationError preserves field-level issues but strips raw submitted input values (passwords, etc.).
4. AIServiceError / Groq failures return a clean generic 502/503 user-facing error with request_id.
5. In production, /docs, /redoc, and /openapi.json are disabled (404).
6. Request-ID header is always returned on responses and matches request_id in body.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from core.database import engine
from services.ai_client import AIServiceError

# We register a dedicated test router to reliably trigger various exceptions
test_router = APIRouter(prefix="/test-errors", tags=["test"])


@test_router.get("/unhandled")
async def trigger_unhandled():
    raise RuntimeError("secret internal database credentials /tmp/secret_key failed")


@test_router.get("/integrity")
async def trigger_integrity():
    raise IntegrityError(
        statement="INSERT INTO users (email) VALUES ('leak@test.com')",
        params={"email": "leak@test.com"},
        orig=Exception("duplicate key value violates unique constraint 'users_email_key'"),
    )


@test_router.get("/ai-error")
async def trigger_ai_error():
    groq_leak = "Groq HTTP 401: {'error': {'message': 'Invalid API Key gsk_1234567890abcdef', 'type': 'invalid_request_error'}}"
    raise AIServiceError(groq_leak)


@pytest.fixture
def prod_client(monkeypatch):
    """Client booted with ENVIRONMENT=production and valid required settings."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "super-strong-production-test-secret-at-least-32-chars-long")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/rolecraft_prod")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.rolecraft.com")
    
    from core.config import get_settings
    get_settings.cache_clear()
    
    import importlib
    import main
    importlib.reload(main)
    
    # Include test router for triggering exceptions directly
    main.app.include_router(test_router)
    
    client = TestClient(main.app, raise_server_exceptions=False)
    yield client
    
    # Reset
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    importlib.reload(main)


def test_docs_and_openapi_disabled_in_production(prod_client: TestClient):
    """In production, /docs, /redoc, and /openapi.json must be disabled."""
    r_docs = prod_client.get("/docs")
    assert r_docs.status_code == 404, f"/docs should be 404 in prod, got {r_docs.status_code}"

    r_redoc = prod_client.get("/redoc")
    assert r_redoc.status_code == 404, f"/redoc should be 404 in prod, got {r_redoc.status_code}"

    r_openapi = prod_client.get("/openapi.json")
    assert r_openapi.status_code == 404, f"/openapi.json should be 404 in prod, got {r_openapi.status_code}"


def test_unhandled_exception_returns_500_with_request_id_and_no_leak(prod_client: TestClient):
    """Unhandled exception must return clean 500 without leaking stack traces or exception details."""
    r = prod_client.get("/test-errors/unhandled")
    assert r.status_code == 500
    data = r.json()
    assert data.get("detail") == "Internal server error"
    assert "request_id" in data
    assert len(data["request_id"]) > 0
    assert r.headers.get("X-Request-ID") == data["request_id"]
    # Ensure none of the sensitive exception text leaked
    assert "secret" not in r.text
    assert "RuntimeError" not in r.text


def test_database_integrity_error_mapped_to_409_clean(prod_client: TestClient):
    """IntegrityError must map to clean 409 without leaking SQL statements, tables, or constraint names."""
    r = prod_client.get("/test-errors/integrity")
    assert r.status_code == 409
    data = r.json()
    assert data.get("detail") == "A conflict occurred with an existing resource."
    assert "request_id" in data
    assert r.headers.get("X-Request-ID") == data["request_id"]
    # Assert no SQL text, table name, or constraint leaked
    assert "users_email_key" not in r.text
    assert "INSERT INTO" not in r.text


def test_request_validation_error_strips_sensitive_input(prod_client: TestClient):
    """Validation errors should keep field error msg and loc, but MUST strip raw submitted input."""
    sensitive_password = "MySuperSecretPlaintextPassword!999"
    # Send an invalid payload where password is too short or missing email
    r = prod_client.post(
        "/auth/signin",
        json={"email": "invalid-email-format", "password": sensitive_password},
    )
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data
    assert "request_id" in data
    assert r.headers.get("X-Request-ID") == data["request_id"]
    
    # Check that errors detail exists
    errors = data["detail"]
    assert isinstance(errors, list)
    for err in errors:
        assert "input" not in err, f"Raw input was leaked in error item: {err}"
    
    # Plaintext password must NOT appear anywhere in the response body
    assert sensitive_password not in r.text


def test_ai_service_error_mapped_to_clean_502(prod_client: TestClient):
    """AIServiceError / Groq failures must return clean user-facing 502 with request_id and no provider keys/bodies."""
    r = prod_client.get("/test-errors/ai-error")
    assert r.status_code == 502
    data = r.json()
    assert data.get("detail") == "AI service is currently unavailable. Please try again later."
    assert "request_id" in data
    assert r.headers.get("X-Request-ID") == data["request_id"]
    # Provider leak checks
    assert "gsk_" not in r.text
    assert "Invalid API Key" not in r.text
    assert "Groq" not in r.text
