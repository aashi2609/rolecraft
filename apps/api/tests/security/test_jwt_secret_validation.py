"""Tests for 1C: JWT secret validation and critical settings startup checks."""
import os
import re

import pytest
from pydantic import ValidationError


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _make_settings(overrides: dict):
    """
    Instantiate Settings with explicit overrides.

    We need to bypass lru_cache and .env loading, so we call the class
    directly with _env_file=None and pass values as constructor kwargs.
    """
    # Clear the lru_cache so each test gets a fresh instance.
    from core.config import get_settings
    get_settings.cache_clear()

    from core.config import Settings
    # Merge sensible defaults for fields the validator doesn't care about
    defaults = {
        "environment": "development",
        "jwt_secret": "",
        "jwt_algorithm": "HS256",
        "database_url": "",
        "cors_origins": "",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


# ──────────────────────────────────────────────────────────────────────
# 1. Production: JWT_SECRET unset → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_without_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET is required"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "",
            "database_url": "postgresql+asyncpg://user:pass@host/db",
            "cors_origins": "https://example.com",
        })


# ──────────────────────────────────────────────────────────────────────
# 2. Production: weak/placeholder JWT_SECRET → startup FAILS
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("weak_secret", [
    "change-me",
    "change-me-to-a-long-random-secret",
    "dev-secret-change-me",
    "secret",
    "supersecret",
    "your-secret-key",
])
def test_production_fails_with_weak_secret(weak_secret):
    with pytest.raises(ValidationError, match="known placeholder"):
        _make_settings({
            "environment": "production",
            "jwt_secret": weak_secret,
            "database_url": "postgresql+asyncpg://user:pass@host/db",
            "cors_origins": "https://example.com",
        })


# ──────────────────────────────────────────────────────────────────────
# 3. Production: short JWT_SECRET → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_with_short_secret():
    with pytest.raises(ValidationError, match="too short"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "only-31-chars-xxxxxxxxxxxxxxxxx",  # 31 chars
            "database_url": "postgresql+asyncpg://user:pass@host/db",
            "cors_origins": "https://example.com",
        })


# ──────────────────────────────────────────────────────────────────────
# 4. Production: strong secret + valid DB + CORS → boots fine
# ──────────────────────────────────────────────────────────────────────

def test_production_boots_with_strong_secret():
    strong = "a" * 64  # 64 chars, not in the weak list
    s = _make_settings({
        "environment": "production",
        "jwt_secret": strong,
        "database_url": "postgresql+asyncpg://user:pass@host/db",
        "cors_origins": "https://example.com",
    })
    assert s.jwt_secret == strong
    assert s.is_production is True


# ──────────────────────────────────────────────────────────────────────
# 5. Development: no secret set → auto-generates random one, boots fine
# ──────────────────────────────────────────────────────────────────────

def test_dev_generates_random_secret_when_unset():
    s = _make_settings({
        "environment": "development",
        "jwt_secret": "",
    })
    assert len(s.jwt_secret) >= 32
    assert s.is_production is False


def test_dev_generates_random_secret_when_weak():
    s = _make_settings({
        "environment": "development",
        "jwt_secret": "dev-secret-change-me",
    })
    # Should have replaced the weak default with a random one
    assert s.jwt_secret != "dev-secret-change-me"
    assert len(s.jwt_secret) >= 32


# ──────────────────────────────────────────────────────────────────────
# 6. Production: DATABASE_URL unset → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_without_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "a" * 64,
            "database_url": "",
            "cors_origins": "https://example.com",
        })


# ──────────────────────────────────────────────────────────────────────
# 7. Production: DATABASE_URL is localhost placeholder → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_with_placeholder_database_url():
    with pytest.raises(ValidationError, match="local placeholder"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "a" * 64,
            "database_url": "postgresql+asyncpg://postgres:postgres@localhost:5432/rolecraft",
            "cors_origins": "https://example.com",
        })


# ──────────────────────────────────────────────────────────────────────
# 8. Production: CORS_ORIGINS unset → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_without_cors_origins():
    with pytest.raises(ValidationError, match="CORS_ORIGINS is required"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "a" * 64,
            "database_url": "postgresql+asyncpg://user:pass@host/db",
            "cors_origins": "",
        })


# ──────────────────────────────────────────────────────────────────────
# 9. Production: CORS_ORIGINS = '*' → startup FAILS
# ──────────────────────────────────────────────────────────────────────

def test_production_fails_with_wildcard_cors():
    with pytest.raises(ValidationError, match="must not contain"):
        _make_settings({
            "environment": "production",
            "jwt_secret": "a" * 64,
            "database_url": "postgresql+asyncpg://user:pass@host/db",
            "cors_origins": "*",
        })


# ──────────────────────────────────────────────────────────────────────
# 10. Development: defaults applied for DATABASE_URL and CORS_ORIGINS
# ──────────────────────────────────────────────────────────────────────

def test_dev_defaults_applied():
    s = _make_settings({
        "environment": "development",
        "jwt_secret": "",
        "database_url": "",
        "cors_origins": "",
    })
    assert "localhost" in s.database_url
    assert "localhost:3000" in s.cors_origins


# ──────────────────────────────────────────────────────────────────────
# 11. No hardcoded default in config.py source code
# ──────────────────────────────────────────────────────────────────────

def test_no_hardcoded_jwt_default_in_source():
    """Ensure the source code doesn't contain the old unsafe default."""
    import inspect
    from core.config import Settings
    source = inspect.getsource(Settings)
    assert "dev-secret-change-me" not in source, (
        "The old hardcoded default 'dev-secret-change-me' is still in config.py"
    )
    # The default should be empty string, not any plaintext secret
    assert 'jwt_secret: str = ""' in source or "jwt_secret: str = ''" in source
