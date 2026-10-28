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
