"""Shared pytest fixtures and environment guards."""

from __future__ import annotations

import os
import sys
import uuid  # Added for fixtures
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


# ── User and Client Fixtures ──────────────────────────────────────────────────

from httpx import AsyncClient
from models import User, UserRole, CandidateProfile, Company, PlanTier, Subscription, SubscriptionStatus
from main import app
import uuid
from core.security import create_access_token


@pytest_asyncio.fixture
async def candidate_user(db_session):
    """Create a candidate user for testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"candidate_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.candidate,
        is_active=True,
        token_version=1
    )
    db_session.add(user)
    
    profile = CandidateProfile(
        user_id=user.id,
        weblinks={"full_name": "Test Candidate"}
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def company_user(db_session):
    """Create a company user for testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"company_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.company,
        is_active=True,
        token_version=1
    )
    db_session.add(user)
    
    company = Company(
        user_id=user.id,
        name="Test Company"
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_company_user(db_session):
    """Create another company user for testing isolation."""
    user = User(
        id=uuid.uuid4(),
        email=f"other_company_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.company,
        is_active=True,
        token_version=1
    )
    db_session.add(user)
    
    company = Company(
        user_id=user.id,
        name="Other Test Company"
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def candidate_client(candidate_user):
    """Authenticated AsyncClient for candidate user."""
    token = create_access_token(user_id=candidate_user.id, role="candidate")
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest_asyncio.fixture
async def company_client(company_user):
    """Authenticated AsyncClient for company user."""
    token = create_access_token(user_id=company_user.id, role="company")
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest_asyncio.fixture
async def other_company_client(other_company_user):
    """Authenticated AsyncClient for other company user."""
    token = create_access_token(user_id=other_company_user.id, role="company")
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest_asyncio.fixture
async def add_plan(db_session):
    """Helper fixture to add subscription plans to users."""
    async def _add_plan(user_id: uuid.UUID, plan_tier: PlanTier):
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            role=UserRole.candidate,
            plan_tier=plan_tier,
            status=SubscriptionStatus.active
        )
        db_session.add(subscription)
        await db_session.commit()
        return subscription
    return _add_plan


@pytest_asyncio.fixture
async def current_admin(db_session):
    """Create or get an admin user for testing."""
    from sqlalchemy import select
    
    # Try to get existing admin
    existing_admin = await db_session.scalar(
        select(User).where(User.role == UserRole.admin).limit(1)
    )
    
    if existing_admin:
        await db_session.refresh(existing_admin)
        return existing_admin
    
    # Create new admin
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.admin,
        is_active=True,
        token_version=1
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


# ── Query Profiling Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def db_profiler():
    """Get or create a database profiler for the current test.
    
    Usage:
        async def test_example(db_profiler):
            # Make queries...
            assert db_profiler.query_count <= 5, f"Expected ≤5 queries, got {db_profiler.query_count}"
    """
    from core.query_profiler import RequestProfiler, set_current_profiler, get_current_profiler
    
    profiler = get_current_profiler()
    if profiler is None:
        profiler = RequestProfiler()
        set_current_profiler(profiler)
    
    profiler.reset()  # Reset at start of each test
    return profiler
