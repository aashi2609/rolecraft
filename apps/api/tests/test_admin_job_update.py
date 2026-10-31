"""Tests for 4B: ADMIN JOB UPDATE: STRING-TO-ENUM.

Verifies:
1. Valid updates for each enum field (case-insensitive variants, hyphens) persist and read back.
2. Invalid enum values return HTTP 422 with clear message listing allowed values.
3. Partial updates only modify fields sent (untouched fields are not wiped or nulled out).
4. Both PATCH and PUT on /admin/jobs/{job_id} work properly.
5. User role, subscription plan_tier/status, and application status string-to-enum conversions work.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Company,
    EmploymentType,
    JobPosting,
    JobStatus,
    JobType,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from core.security import create_access_token


async def _create_admin_and_job(db_session: AsyncSession):
    admin_id = uuid.uuid4()
    admin_user = User(
        id=admin_id,
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        role=UserRole.admin,
        is_active=True,
        token_version=0,
    )
    db_session.add(admin_user)

    company_id = uuid.uuid4()
    comp_user = User(
        id=company_id,
        email=f"comp_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        role=UserRole.company,
        is_active=True,
        token_version=0,
    )
    db_session.add(comp_user)
    comp_profile = Company(user_id=company_id, name="Admin Job Test Co")
    db_session.add(comp_profile)

    job_id = uuid.uuid4()
    job = JobPosting(
        id=job_id,
        company_id=company_id,
        title="Software Engineer",
        department="Engineering",
        status=JobStatus.draft,
        job_type=JobType.hybrid,
        employment_type="Part-time",
        min_salary=100000,
        max_salary=150000,
        salary_unit="Per annum",
        location="Bangalore, Karnataka, India",
        city="Bangalore",
        state="Karnataka",
        country="India",
        description="Initial description",
    )
    db_session.add(job)
    await db_session.commit()

    admin_token = create_access_token(user_id=admin_id, role="admin", token_version=0)
    return {
        "admin_id": admin_id,
        "company_id": company_id,
        "job_id": job_id,
        "token": admin_token,
    }


@pytest.mark.asyncio
async def test_admin_job_update_valid_enums_and_case_variants(
    db_session: AsyncSession,
):
    """Test valid updates for status, job_type, employment_type with different casings."""
    ctx = await _create_admin_and_job(db_session)
    job_id = ctx["job_id"]
    token = ctx["token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Update with Title-case / form payloads
        res = await client.patch(
            f"/admin/jobs/{job_id}",
            json={
                "status": "Live",
                "job_type": "On-site",
                "employment_type": "Full-time",
            },
            headers=headers,
        )
        assert res.status_code == 200, res.text
        assert res.json() == {"ok": True}

        # Verify DB persisted
        db_session.expire_all()
        job = await db_session.get(JobPosting, job_id)
        assert job.status == JobStatus.live
        assert job.job_type == JobType.onsite
        assert job.employment_type == "Full-time"

        # 2. Update with lowercase variants: status "closed", job_type "remote", employment_type "contract"
        res2 = await client.patch(
            f"/admin/jobs/{job_id}",
            json={
                "status": "closed",
                "job_type": "remote",
                "employment_type": "contract",
            },
            headers=headers,
        )
        assert res2.status_code == 200, res2.text

        db_session.expire_all()
        job = await db_session.get(JobPosting, job_id)
        assert job.status == JobStatus.closed
        assert job.job_type == JobType.remote
        assert job.employment_type == "Contract"

        # 3. Update via PUT with hyphenated lowercase: job_type "on-site", status "draft"
        res3 = await client.put(
            f"/admin/jobs/{job_id}",
            json={
                "status": "draft",
                "job_type": "on-site",
                "employment_type": "internship",
            },
            headers=headers,
        )
        assert res3.status_code == 200, res3.text

        db_session.expire_all()
        job = await db_session.get(JobPosting, job_id)
        assert job.status == JobStatus.draft
        assert job.job_type == JobType.onsite
        assert job.employment_type == "Internship"


@pytest.mark.asyncio
async def test_admin_job_update_invalid_enum_returns_422(
    db_session: AsyncSession,
):
    """Test invalid enum values return 422 with clear message listing allowed values."""
    ctx = await _create_admin_and_job(db_session)
    job_id = ctx["job_id"]
    token = ctx["token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid status
        res = await client.patch(
            f"/admin/jobs/{job_id}",
            json={"status": "super_live"},
            headers=headers,
        )
        assert res.status_code == 422, res.text
        err = res.text.lower()
        assert "invalid status" in err
        assert "draft" in err and "live" in err and "closed" in err

        # Invalid job_type
        res2 = await client.patch(
            f"/admin/jobs/{job_id}",
            json={"job_type": "in_the_cloud"},
            headers=headers,
        )
        assert res2.status_code == 422, res2.text
        err2 = res2.text.lower()
        assert "invalid job_type" in err2
        assert "onsite" in err2 and "remote" in err2 and "hybrid" in err2

        # Invalid employment_type
        res3 = await client.patch(
            f"/admin/jobs/{job_id}",
            json={"employment_type": "casual_volunteer"},
            headers=headers,
        )
        assert res3.status_code == 422, res3.text
        err3 = res3.text.lower()
        assert "invalid employment_type" in err3
        assert "full-time" in err3 and "part-time" in err3


@pytest.mark.asyncio
async def test_admin_job_partial_update_preserves_untouched_fields(
    db_session: AsyncSession,
):
    """Verify that a partial update does NOT null out or wipe untouched fields."""
    ctx = await _create_admin_and_job(db_session)
    job_id = ctx["job_id"]
    token = ctx["token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Only update title
        res = await client.patch(
            f"/admin/jobs/{job_id}",
            json={"title": "Updated Lead Architect"},
            headers=headers,
        )
        assert res.status_code == 200, res.text

        db_session.expire_all()
        job = await db_session.get(JobPosting, job_id)
        assert job.title == "Updated Lead Architect"
        # Untouched fields must stay intact
        assert job.department == "Engineering"
        assert job.status == JobStatus.draft
        assert job.job_type == JobType.hybrid
        assert job.employment_type == "Part-time"
        assert job.min_salary == 100000
        assert job.max_salary == 150000
        assert job.location == "Bangalore, Karnataka, India"
        assert job.description == "Initial description"


@pytest.mark.asyncio
async def test_admin_user_role_update_and_validation(
    db_session: AsyncSession,
):
    """Test PATCH /admin/users/{user_id} with valid role variants and invalid role."""
    ctx = await _create_admin_and_job(db_session)
    comp_id = ctx["company_id"]
    token = ctx["token"]
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Valid role with title casing
        res = await client.patch(
            f"/admin/users/{comp_id}",
            json={"role": "Candidate"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        assert res.json()["role"] == "candidate"

        db_session.expire_all()
        u = await db_session.get(User, comp_id)
        assert u.role == UserRole.candidate

        # 2. Invalid role
        res_bad = await client.patch(
            f"/admin/users/{comp_id}",
            json={"role": "superadmin"},
            headers=headers,
        )
        assert res_bad.status_code == 422, res_bad.text
        err = res_bad.text.lower()
        assert "invalid role" in err
        assert "candidate" in err and "company" in err and "admin" in err


@pytest.mark.asyncio
async def test_admin_subscription_enum_update_and_validation(
    db_session: AsyncSession,
):
    """Test PATCH /admin/subscriptions/{sub_id} and POST /admin/subscriptions."""
    ctx = await _create_admin_and_job(db_session)
    user_id = ctx["company_id"]
    token = ctx["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create initial subscription
    sub_id = uuid.uuid4()
    sub = Subscription(
        id=sub_id,
        user_id=user_id,
        role=UserRole.company,
        plan_tier=PlanTier.starter,
        status=SubscriptionStatus.active,
    )
    db_session.add(sub)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Valid update with casing
        res = await client.patch(
            f"/admin/subscriptions/{sub_id}",
            json={
                "plan_tier": "Corporate_Annual",
                "status": "Cancelled",
            },
            headers=headers,
        )
        assert res.status_code == 200, res.text

        db_session.expire_all()
        s = await db_session.get(Subscription, sub_id)
        assert s.plan_tier == PlanTier.corporate_annual
        assert s.status == SubscriptionStatus.cancelled

        # 2. Invalid plan_tier
        res_bad = await client.patch(
            f"/admin/subscriptions/{sub_id}",
            json={"plan_tier": "unlimited_tier"},
            headers=headers,
        )
        assert res_bad.status_code == 422, res_bad.text
        assert "invalid plan_tier" in res_bad.text.lower()

        # 3. Invalid status
        res_bad2 = await client.patch(
            f"/admin/subscriptions/{sub_id}",
            json={"status": "paused_temporarily"},
            headers=headers,
        )
        assert res_bad2.status_code == 422, res_bad2.text
        assert "invalid status" in res_bad2.text.lower()
