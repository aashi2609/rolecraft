"""Shared pytest fixtures and environment guards."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure apps/api root is in sys.path
api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

# Load .env file explicitly so TEST_DATABASE_URL is populated
from dotenv import load_dotenv
load_dotenv(Path(api_root) / ".env")

# ── Snapshot any pre-override DATABASE_URL ──
_PRIMARY_URL_SNAPSHOT = (
    os.getenv("PRIMARY_DATABASE_URL", "").strip()
    or os.getenv("DATABASE_URL", "").strip()
)

# ── CRITICAL: Set DATABASE_URL to TEST_DATABASE_URL BEFORE any app imports ──
_test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url

import pytest

# Fail loudly if run on the wrong interpreter.
# Deploy target (Render runtime.txt / render.yaml): Python 3.11.9
# CI and local must be >= 3.10; prefer 3.11.x to match deploy.
if sys.version_info[:2] < (3, 10):
    raise RuntimeError(
        f"Wrong Python interpreter: {sys.version.split()[0]} "
        f"({sys.executable}). Expected Python >= 3.10 (deploy target: 3.11.9)."
    )


from core.config import get_settings
from core.db_guard import enforce_isolated_test_database


@pytest.fixture(scope="session", autouse=True)
def _assert_python_version() -> None:
    assert sys.version_info[:2] >= (
        3,
        10,
    ), f"Tests require Python >= 3.10, got {sys.version} from {sys.executable}"


def pytest_sessionstart(session: pytest.Session) -> None:
    """Validate database isolation at the very start of the pytest session."""
    from core.database import engine
    from core.db_guard import extract_db_identity, is_primary_endpoint, PRIMARY_DB_NAME

    eng_info = extract_db_identity(str(engine.url))
    if is_primary_endpoint(eng_info[0]):
        pytest.exit(
            f"FATAL: Engine URL endpoint '{eng_info[0]}' matches primary denylist! Session aborted.",
            returncode=1,
        )
    if is_primary_endpoint(eng_info[0]) and eng_info[1] == PRIMARY_DB_NAME:
        pytest.exit(
            f"FATAL: Engine resolves to primary database {eng_info[0]}/{eng_info[1]}! Session aborted.",
            returncode=1,
        )


    from core.config import get_settings
    settings = get_settings()
    settings.storage_backend = "local"
    settings.rate_limit_enabled = False
    from core.rate_limit import reset_rate_limit_backends, limiter
    reset_rate_limit_backends()
    limiter.enabled = False

    # Reconfigure engine with NullPool so connections do not leak across event loops
    from core import database
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    db_url, connect_args = database.asyncpg_engine_kwargs(os.environ["DATABASE_URL"])
    database.engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
        connect_args=connect_args,
    )
    database.AsyncSessionLocal = async_sessionmaker(
        database.engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed required static test users (admin and cancelled company)
    import asyncio
    from sqlalchemy import text

    async def _seed_test_users():
        async with database.engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO users (id, email, password_hash, role, is_active, token_version)
                VALUES ('b55c77e8-1a01-4f9c-a1ff-4568879121c7', 'admin@acme.com', '$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6', 'admin', true, 1)
                ON CONFLICT (id) DO UPDATE SET token_version = 1, is_active = true, role = 'admin';
            """))
            await conn.execute(text("""
                INSERT INTO users (id, email, password_hash, role, is_active, token_version)
                VALUES ('5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1', 'kauraashi26@gmail.com', '$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6', 'company', true, 1)
                ON CONFLICT (id) DO UPDATE SET token_version = 1, is_active = true, role = 'company';
            """))
            await conn.execute(text("""
                INSERT INTO companies (user_id, name)
                VALUES ('5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1', 'Aashi Corp')
                ON CONFLICT (user_id) DO NOTHING;
            """))
            await conn.execute(text("""
                INSERT INTO subscriptions (id, user_id, role, plan_tier, status)
                VALUES ('5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de2', '5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1', 'company', 'starter', 'cancelled')
                ON CONFLICT (id) DO UPDATE SET status = 'cancelled';
            """))
            await conn.execute(text("""
                INSERT INTO users (id, email, password_hash, role, is_active, token_version)
                VALUES ('85e85c0d-327c-40ad-be00-e794354224c5', 'kauraashi8777@gmail.com', '$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6', 'candidate', true, 1)
                ON CONFLICT (id) DO UPDATE SET token_version = 1, is_active = true, role = 'candidate';
            """))
            await conn.execute(
                text("""
                    INSERT INTO candidate_profiles (user_id, weblinks)
                    VALUES ('85e85c0d-327c-40ad-be00-e794354224c5', CAST(:weblinks AS jsonb))
                    ON CONFLICT (user_id) DO NOTHING;
                """),
                {"weblinks": '{"full_name": "Aashi Candidate"}'},
            )

    try:
        asyncio.run(_seed_test_users())
    except Exception as exc:
        print(f"Warning: seeding static test users failed: {exc}")


@pytest.fixture(autouse=True)
def _enforce_test_database_guard(request) -> None:
    # Skip guard for db_guard unit tests (they test the guard logic itself)
    nodeid = getattr(request.node, "nodeid", "") or ""
    if "test_db_guard" in nodeid:
        return
    if request.node.get_closest_marker("skip_db_guard"):
        return

    test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
    # Pass pre-override snapshot so we don't compare test URL to itself after rewrite.
    # Denylist remains the authoritative primary check.
    enforce_isolated_test_database(test_db_url, _PRIMARY_URL_SNAPSHOT or None)


@pytest.fixture(autouse=True)
def _ensure_test_config(monkeypatch) -> None:
    from core.config import get_settings
    monkeypatch.setattr(get_settings(), "storage_backend", "local")
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)
    from core.rate_limit import limiter
    limiter.enabled = False


import pytest_asyncio


@pytest_asyncio.fixture
async def db_session():
    """Isolated async db session for unit/integration tests."""
    from core.database import asyncpg_engine_kwargs
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
    db_url, connect_args = asyncpg_engine_kwargs(test_db_url)
    connect_args["statement_cache_size"] = 0
    engine = create_async_engine(db_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()
