"""Unit and integration tests for plan limits and get_user_plan entitlement."""

import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import check_plan_limit, get_user_plan
from models import (
    CandidateProfile,
    Company,
    JobPosting,
    JobStatus,
    PlanTier,
    Resume,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)


@pytest.mark.asyncio
async def test_get_user_plan_no_subscription_returns_none(db_session: AsyncSession):
    """A user with no subscription record receives no entitlement (None)."""
    user = User(
        id=uuid.uuid4(),
        email=f"noplan_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    plan = await get_user_plan(user, db_session)
    assert plan is None, f"Expected None, got {plan}"


@pytest.mark.asyncio
async def test_get_user_plan_cancelled_subscription_returns_none(db_session: AsyncSession):
    """A user with only cancelled subscriptions receives no entitlement (None)."""
    user = User(
        id=uuid.uuid4(),
        email=f"cancelled_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.company,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        role=UserRole.company,
        plan_tier=PlanTier.corporate_annual,
        status=SubscriptionStatus.cancelled,
    )
    db_session.add(sub)
    await db_session.flush()

    plan = await get_user_plan(user, db_session)
    assert plan is None, f"Expected None for cancelled subscription, got {plan}"


@pytest.mark.asyncio
async def test_get_user_plan_active_subscription_returns_tier(db_session: AsyncSession):
    """A user with an active subscription receives their active plan_tier."""
    user = User(
        id=uuid.uuid4(),
        email=f"active_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        role=UserRole.candidate,
        plan_tier=PlanTier.complete,
        status=SubscriptionStatus.active,
    )
    db_session.add(sub)
    await db_session.flush()

    plan = await get_user_plan(user, db_session)
    assert plan == PlanTier.complete, f"Expected PlanTier.complete, got {plan}"


@pytest.mark.asyncio
async def test_candidate_free_resume_limit_enforced(db_session: AsyncSession):
    """Free candidate: 1 resume slot allowed. Second generation raises 403."""
    user = User(
        id=uuid.uuid4(),
        email=f"cand_limit_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(user)
    profile = CandidateProfile(user_id=user.id)
    db_session.add(profile)
    await db_session.flush()

    # 1. Zero resumes: extra=1 allowed
    await check_plan_limit(user, db_session, "resume_verticals", extra=1)

    # 2. Zero resumes: requesting extra=2 at once blocked
    with pytest.raises(HTTPException) as exc_info:
        await check_plan_limit(user, db_session, "resume_verticals", extra=2)
    assert exc_info.value.status_code == 403
    assert "Free plan allows 1 target role at a time" in exc_info.value.detail

    # 3. Add 1 resume to database
    resume = Resume(
        id=uuid.uuid4(),
        candidate_id=user.id,
        target_vertical="Engineering",
        content={"summary": "test"},
        embedding=[0.0] * 1536,
    )
    db_session.add(resume)
    await db_session.flush()

    # 4. With 1 resume existing, requesting another resume is blocked
    with pytest.raises(HTTPException) as exc_info:
        await check_plan_limit(user, db_session, "resume_verticals", extra=1)
    assert exc_info.value.status_code == 403
    assert "Free plan resume cap reached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_paid_candidate_unlimited_resumes(db_session: AsyncSession):
    """Paid candidate (complete plan): unlimited resume slots allowed."""
    user = User(
        id=uuid.uuid4(),
        email=f"cand_paid_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(user)
    profile = CandidateProfile(user_id=user.id)
    db_session.add(profile)
    await db_session.flush()

    sub = Subscription(
        id=uuid.uuid4(),
        user_id=user.id,
        role=UserRole.candidate,
        plan_tier=PlanTier.complete,
        status=SubscriptionStatus.active,
    )
    db_session.add(sub)
    await db_session.flush()

    # Add 5 resumes
    for i in range(5):
        r = Resume(
            id=uuid.uuid4(),
            candidate_id=user.id,
            target_vertical=f"Vertical {i}",
            content={"summary": "test"},
            embedding=[0.0] * 1536,
        )
        db_session.add(r)
    await db_session.flush()

    # Should not raise
    await check_plan_limit(user, db_session, "resume_verticals", extra=3)


@pytest.mark.asyncio
async def test_company_free_job_postings_limit_enforced(db_session: AsyncSession):
    """Free company (no subscription): allows up to 2 active jobs; 3rd is blocked with 403."""
    user = User(
        id=uuid.uuid4(),
        email=f"co_limit_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake",
        role=UserRole.company,
        is_active=True,
    )
    db_session.add(user)
    company = Company(user_id=user.id, name="Test Company")
    db_session.add(company)
    await db_session.flush()

    # Zero jobs: allowed
    await check_plan_limit(user, db_session, "job_postings")

    # Add 2 live jobs
    for i in range(2):
        jp = JobPosting(
            id=uuid.uuid4(),
            company_id=user.id,
            title=f"Job {i}",
            description="test",
            status=JobStatus.live,
        )
        db_session.add(jp)
    await db_session.flush()

    # 3rd job is blocked
    with pytest.raises(HTTPException) as exc_info:
        await check_plan_limit(user, db_session, "job_postings")
    assert exc_info.value.status_code == 403
    assert "Free plan allows up to 2 active job postings" in exc_info.value.detail


@pytest.mark.skip_db_guard
def test_check_plan_limit_ast_no_unconditional_return():
    """Static AST guard: fails if check_plan_limit has an early return or bypass keyword."""
    import ast
    import inspect
    from core.dependencies import check_plan_limit

    source = inspect.getsource(check_plan_limit)
    # 1. No bypass keywords in source
    for kw in ["bypass", "temporarily", "return none"]:
        assert kw not in source.lower(), f"Forbidden short-circuit keyword '{kw}' found in check_plan_limit source!"

    # 2. Parse AST: ensure no top-level Return statement precedes plan gating logic
    tree = ast.parse(source)
    func_def = tree.body[0]
    # Filter out docstring
    body_nodes = [
        n for n in func_def.body
        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    ]
    assert not isinstance(body_nodes[0], ast.Return), (
        f"check_plan_limit has an unconditional early return at top of function!"
    )


@pytest.mark.skip_db_guard
@pytest.mark.asyncio
async def test_check_plan_limit_unit_enforcement_raises_on_excess():
    """Unit test with mock AsyncSession: asserts check_plan_limit raises 403 and never returns None on excess."""
    from unittest.mock import AsyncMock, MagicMock
    from core.dependencies import check_plan_limit

    mock_db = MagicMock(spec=AsyncSession)
    user = User(
        id=uuid.uuid4(),
        email="test_guard@example.com",
        password_hash="fake",
        role=UserRole.candidate,
        is_active=True,
    )

    # Mock execute for get_user_plan -> None
    mock_result_sub = MagicMock()
    mock_result_sub.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result_sub)

    # Mock scalar for existing resume count = 1
    mock_db.scalar = AsyncMock(return_value=1)

    # Must raise HTTPException(403); if short-circuited (returns None), test FAILS
    with pytest.raises(HTTPException) as exc_info:
        await check_plan_limit(user, mock_db, "resume_verticals", extra=1)
    assert exc_info.value.status_code == 403
    assert "Free plan resume cap reached" in exc_info.value.detail

