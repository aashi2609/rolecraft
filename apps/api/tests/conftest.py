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

# ── CRITICAL: Set DATABASE_URL to TEST_DATABASE_URL BEFORE any app imports ──
_test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url

# Now safe to import modules that depend on DATABASE_URL
import uuid  # Added for fixtures
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import get_settings
from core.database import asyncpg_engine_kwargs
from core.db_guard import (
    enforce_isolated_test_database,
    extract_db_identity,
    is_primary_endpoint,
    PRIMARY_DB_NAME,
)
from core.rate_limit import reset_rate_limit_backends, limiter
from main import app
from models import (
    User,
    UserRole,
    CandidateProfile,
    Company,
    PlanTier,
    Subscription,
    SubscriptionStatus,
)
from core.security import create_access_token

# Fail loudly if run on the wrong interpreter.
# Deploy target (Render runtime.txt / render.yaml): Python 3.11.9
# CI and local must be >= 3.10; prefer 3.11.x to match deploy.
if sys.version_info[:2] < (3, 10):
    raise RuntimeError(
        f"Wrong Python interpreter: {sys.version.split()[0]} "
        f"({sys.executable}). Expected Python >= 3.10 (deploy target: 3.11.9)."
    )


@pytest.fixture(scope="session", autouse=True)
def _assert_python_version() -> None:
    assert sys.version_info[:2] >= (
        3,
        10,
    ), f"Tests require Python >= 3.10, got {sys.version} from {sys.executable}"


def pytest_sessionstart(session: pytest.Session) -> None:
    """Validate database isolation at the very start of the pytest session."""
    from core.database import engine

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

    settings = get_settings()
    settings.storage_backend = "local"
    settings.rate_limit_enabled = False
    reset_rate_limit_backends()
    limiter.enabled = False


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
    enforce_isolated_test_database(test_db_url, None)


@pytest.fixture(autouse=True)
def _ensure_test_config(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "storage_backend", "local")
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)
    limiter.enabled = False


@pytest_asyncio.fixture
async def db_session():
    """Isolated async db session for unit/integration tests.

    Binds session to a connection with an outer transaction begun,
    then creates a savepoint for each test that rolls back on teardown.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
    db_url, connect_args = asyncpg_engine_kwargs(test_db_url)
    connect_args["statement_cache_size"] = 0
    engine = create_async_engine(db_url, connect_args=connect_args)
    
    # Begin outer transaction
    async with engine.begin() as connection:
        # Bind session to connection, not engine
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
            await session.rollback()
    
    await engine.dispose()


@pytest.fixture(autouse=True)
async def leak_detector(db_session):
    """Strict leak detector: fails test if any rows remain after rollback."""
    yield
    # After test completes and rollback, check for data leaks
    from sqlalchemy import text
    
    # Get all table names except alembic_version
    tables_query = text("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename != 'alembic_version'
    """)
    result = await db_session.execute(tables_query)
    tables = [row[0] for row in result.fetchall()]
    
    leaked_data = []
    for table in tables:
        count_query = text(f"SELECT COUNT(*) FROM {table}")
        count_result = await db_session.execute(count_query)
        count = count_result.scalar()
        if count > 0:
            leaked_data.append(f"{table}: {count} rows")
    
    if leaked_data:
        pytest.fail(f"Data leak detected after test rollback:\n" + "\n".join(leaked_data))


# ── User and Client Fixtures ──────────────────────────────────────────────────


@pytest_asyncio.fixture
async def candidate_user(db_session):
    """Create a candidate user for testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"candidate_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.candidate,
        is_active=True,
        token_version=1,
    )
    db_session.add(user)

    profile = CandidateProfile(user_id=user.id, weblinks={"full_name": "Test Candidate"})
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
        token_version=1,
    )
    db_session.add(user)

    company = Company(user_id=user.id, name="Test Company")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def make_company(db_session):
    """Create a company user with profile."""
    async def _make_company(company_id: uuid.UUID | None = None):
        cid = company_id or uuid.uuid4()
        user = User(
            id=cid,
            email=f"company_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",
            role=UserRole.company,
            is_active=True,
            token_version=1,
        )
        db_session.add(user)
        company = Company(user_id=cid, name="Test Company")
        db_session.add(company)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _make_company


@pytest_asyncio.fixture
async def other_company_user(db_session):
    """Create another company user for testing isolation."""
    user = User(
        id=uuid.uuid4(),
        email=f"other_company_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.company,
        is_active=True,
        token_version=1,
    )
    db_session.add(user)

    company = Company(user_id=user.id, name="Other Test Company")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create or get an admin user for testing. Uses fixed UUID so tests are idempotent."""
    admin_id = uuid.UUID("b55c77e8-1a01-4f9c-a1ff-4568879121c7")
    
    # Always try to fetch first - don't assume it doesn't exist
    existing = await db_session.scalar(select(User).where(User.id == admin_id))
    if existing:
        # Ensure detached state - expunge and re-merge to avoid session issues
        db_session.expunge(existing)
        existing = await db_session.scalar(select(User).where(User.id == admin_id))
        return existing
    
    # Create new only if truly doesn't exist
    user = User(
        id=admin_id,
        email="admin@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.admin,
        is_active=True,
        token_version=1,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unpaid_company_user(db_session):
    """Create or get a company user with cancelled subscription for testing unpaid access."""
    company_id = uuid.UUID("5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1")
    
    # Always try to fetch first
    existing = await db_session.scalar(select(User).where(User.id == company_id))
    if existing:
        db_session.expunge(existing)
        existing = await db_session.scalar(select(User).where(User.id == company_id))
        return existing
    
    # Create new only if doesn't exist
    user = User(
        id=company_id,
        email="unpaid_company@test.com",
        password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",  # "password"
        role=UserRole.company,
        is_active=True,
        token_version=1,
    )
    db_session.add(user)

    company = Company(user_id=user.id, name="Unpaid Company")
    db_session.add(company)
    
    # Create cancelled subscription
    subscription = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        role=UserRole.company,
        plan_tier=PlanTier.starter,
        status=SubscriptionStatus.cancelled,
    )
    db_session.add(subscription)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def candidate_client(candidate_user, db_session):
    """Authenticated AsyncClient for candidate user."""
    from httpx import ASGITransport
    from core.database import get_db
    
    # Override get_db to use test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    token = create_access_token(user_id=candidate_user.id, role="candidate")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def company_client(company_user, db_session):
    """Authenticated AsyncClient for company user."""
    from httpx import ASGITransport
    from core.database import get_db
    
    # Override get_db to use test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    token = create_access_token(user_id=company_user.id, role="company")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def other_company_client(other_company_user, db_session):
    """Authenticated AsyncClient for other company user."""
    from httpx import ASGITransport
    from core.database import get_db
    
    # Override get_db to use test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    token = create_access_token(user_id=other_company_user.id, role="company")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def add_plan(db_session):
    """Helper fixture to add subscription plans to users."""

    async def _add_plan(user_id: uuid.UUID, plan_tier: PlanTier):
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            role=UserRole.candidate,
            plan_tier=plan_tier,
            status=SubscriptionStatus.active,
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
        token_version=1,
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
    from core.query_profiler import (
        RequestProfiler,
        set_current_profiler,
        get_current_profiler,
    )

    profiler = get_current_profiler()
    if profiler is None:
        profiler = RequestProfiler()
        set_current_profiler(profiler)

    profiler.reset()  # Reset at start of each test
    return profiler


# ── Additional Fixture Factories for Complete Test Coverage ────────────────────


@pytest_asyncio.fixture
async def grant_plan(db_session):
    """Grant a specific plan with optional status and expiry to a user."""

    async def _grant_plan(
        user_id: uuid.UUID,
        plan_tier: PlanTier = PlanTier.complete,
        status: SubscriptionStatus = SubscriptionStatus.active,
    ):
        # Remove existing subscription if any
        existing = (
            (await db_session.execute(select(Subscription).where(Subscription.user_id == user_id)))
            .scalars()
            .all()
        )
        for sub in existing:
            await db_session.delete(sub)

        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            role=UserRole.candidate,
            plan_tier=plan_tier,
            status=status,
        )
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        return subscription

    return _grant_plan


@pytest_asyncio.fixture
async def make_job(db_session, company_user):
    """Create a job posting with specified status and details."""

    async def _make_job(
        title: str = "Senior Software Engineer",
        status: str = "published",
        description: str = "Join our team",
        **kwargs,
    ):
        from models import Job, JobStatus
        from datetime import datetime

        job_kwargs = {
            "id": uuid.uuid4(),
            "company_id": company_user.id,
            "title": title,
            "description": description,
            "salary_min": kwargs.get("salary_min", 80000),
            "salary_max": kwargs.get("salary_max", 120000),
            "job_role": kwargs.get("job_role", "backend"),
            "job_level": kwargs.get("job_level", "mid"),
            "job_type": kwargs.get("job_type", "full_time"),
            "location": kwargs.get("location", "Remote"),
            "required_experience_years": kwargs.get("required_experience_years", 3),
            "skills": kwargs.get("skills", ["Python", "FastAPI"]),
            "status": JobStatus(status) if isinstance(status, str) else status,
            "posted_at": datetime.utcnow(),
        }
        job = Job(**job_kwargs)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job

    return _make_job


@pytest_asyncio.fixture
async def make_application(db_session, candidate_user):
    """Create a job application."""

    async def _make_application(job_id: uuid.UUID, status: str = "submitted", **kwargs):
        from models import Application, ApplicationStatus
        from datetime import datetime

        application = Application(
            id=uuid.uuid4(),
            candidate_id=candidate_user.id,
            job_id=job_id,
            status=ApplicationStatus(status) if isinstance(status, str) else status,
            applied_at=datetime.utcnow(),
        )
        db_session.add(application)
        await db_session.commit()
        await db_session.refresh(application)
        return application

    return _make_application


@pytest_asyncio.fixture
async def make_conversation(db_session, candidate_user, company_user):
    """Create a conversation between candidate and company."""

    async def _make_conversation(
        candidate_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
    ):
        from models import Conversation, CandidateProfile, Company, User, UserRole
        from datetime import datetime

        # Use defaults if not provided
        final_candidate_id = candidate_id or candidate_user.id
        final_company_id = company_id or company_user.id

        # Ensure candidate profile exists if we're using a custom ID
        if candidate_id and candidate_id != candidate_user.id:
            existing_candidate = await db_session.get(User, candidate_id)
            if not existing_candidate:
                # Create user + profile for the candidate
                user = User(
                    id=candidate_id,
                    email=f"candidate_{uuid.uuid4().hex[:8]}@test.com",
                    password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",
                    role=UserRole.candidate,
                    is_active=True,
                    token_version=1,
                )
                db_session.add(user)
                profile = CandidateProfile(user_id=candidate_id, weblinks={"full_name": "Test Candidate"})
                db_session.add(profile)
                await db_session.flush()

        # Ensure company exists if we're using a custom ID
        if company_id and company_id != company_user.id:
            existing_company = await db_session.get(Company, company_id)
            if not existing_company:
                # Create user + company for the company
                user = User(
                    id=company_id,
                    email=f"company_{uuid.uuid4().hex[:8]}@test.com",
                    password_hash="$2b$12$e/a.vjWwM2n06o0rLzT4U.kI441E7.3d88bY1L9Gg7Y65vYvX/jO6",
                    role=UserRole.company,
                    is_active=True,
                    token_version=1,
                )
                db_session.add(user)
                company = Company(user_id=company_id, name="Test Company")
                db_session.add(company)
                await db_session.flush()

        conv = Conversation(
            id=uuid.uuid4(),
            candidate_id=final_candidate_id,
            company_id=final_company_id,
            job_id=job_id,
            created_at=datetime.utcnow(),
            last_message_at=datetime.utcnow(),
        )
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)
        return conv

    return _make_conversation


@pytest_asyncio.fixture
async def make_message(db_session):
    """Create a message in a conversation."""

    async def _make_message(
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        body: str = "Test message",
        sender_role: str = "company",
        **kwargs,
    ):
        from models import Message
        from datetime import datetime

        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_role=sender_role,
            body=body,
            sent_at=datetime.utcnow(),
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        return message

    return _make_message


@pytest.fixture
def mock_ai_service(monkeypatch):
    """Mock Groq AI provider with deterministic responses.

    Usage:
        async def test_something(mock_ai_service):
            # AI calls will return mock responses deterministically
    """

    class MockAIService:
        async def generate_resume(self, candidate_id: uuid.UUID, force_deterministic: bool = False):
            return {
                "id": uuid.uuid4(),
                "candidate_id": candidate_id,
                "content": "Mock Resume:\n\nSummary: Senior Software Engineer\n\nExperience: 5+ years",
                "status": "generated",
                "generated_from_profile_at": None,
                "is_stale": False,
            }

        async def parse_resume_pdf(self, file_path: str):
            return {
                "full_name": "Mock Candidate",
                "skills": ["Python", "React", "FastAPI"],
                "experience_years": 5,
                "current_title": "Senior Engineer",
            }

        async def get_ats_score(self, resume_id: uuid.UUID, job_id: uuid.UUID):
            return {
                "score": 85,
                "match_percentage": 85.0,
                "feedback": "Strong match for the role",
                "missing_skills": [],
            }

        async def get_fitment_rationale(self, candidate_id: uuid.UUID, job_id: uuid.UUID):
            return {
                "rationale": "Mock rationale: Candidate has strong Python skills matching job requirements",
                "source": "template",
            }

    mock = MockAIService()
    monkeypatch.setattr("services.ai_service", mock, raising=False)
    monkeypatch.setattr("core.ai_client", mock, raising=False)
    return mock


@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service to prevent real email sends."""

    class MockEmailService:
        sent_emails = []

        async def send_email(self, to: str, subject: str, template: str, **kwargs):
            self.sent_emails.append(
                {
                    "to": to,
                    "subject": subject,
                    "template": template,
                    "context": kwargs,
                }
            )
            return True

        def clear(self):
            self.sent_emails = []

    mock = MockEmailService()
    monkeypatch.setattr("core.email_service", mock, raising=False)
    return mock


@pytest.fixture(scope="session", autouse=True)
def verify_no_external_calls():
    """Ensure tests do not make external network calls (except to test DB).

    Note: This is a placeholder. Full pytest-socket integration depends on
    whether the test needs to block all external calls or just specific ones.
    Neon Postgres connections are HTTPS and are acceptable for integration tests.
    """
    import os

    test_db_url = os.getenv("TEST_DATABASE_URL", "")
    allowed_hosts = []
    if "neon.tech" in test_db_url:
        # Extract host from URL
        from urllib.parse import urlparse

        parsed = urlparse(test_db_url)
        allowed_hosts.append(parsed.hostname)

    # pytest-socket would be configured here when needed
    # For now, this is a placeholder that documents the intent
    pass


@pytest.fixture(scope="session", autouse=True)
async def empty_tables_check():
    """After all tests, assert every table is empty (transactional isolation check)."""
    yield  # Let tests run first
    
    # After all tests: check all tables are empty
    test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL not set, skipping empty table check")
        return
    
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import inspect, text
    
    db_url, connect_args = asyncpg_engine_kwargs(test_db_url)
    engine = create_async_engine(db_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        # Get all table names
        inspector = inspect(engine.sync_engine)
        tables = inspector.get_table_names()
        
        # Check each table for rows
        for table in tables:
            if table.startswith("alembic"):  # Skip Alembic's internal tables
                continue
            result = await session.execute(text(f"SELECT COUNT(*) as cnt FROM {table}"))
            count = result.scalar()
            assert count == 0, f"Table {table} is not empty after tests (found {count} rows). Isolation failed!"
    
    await engine.dispose()
