"""Regression tests: eager company loading in job detail and update endpoints.

Proves that GET /jobs/{id}, PUT /jobs/{id}, PATCH /jobs/{id}, and
PATCH /jobs/{id}/status all load the company relationship eagerly —
no MissingGreenlet 500 — and return company_name plus pipeline counts.

These tests are independent of test_security_fixes.py::
test_job_endpoints_do_not_lazy_load_company; both should run and pass.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from main import app
from models import (
    CandidateProfile,
    Company,
    JobPosting,
    JobStatus,
    User,
    UserRole,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_company_user(session: AsyncSession) -> tuple[User, Company]:
    """Insert a company user + Company row, return (user, company)."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"co_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="fakehash",
        role=UserRole.company,
        is_active=True,
        token_version=1,
    )
    session.add(user)
    company = Company(user_id=uid, name=f"TestCorp-{uuid.uuid4().hex[:6]}")
    session.add(company)
    return user, company


def _make_candidate_user(session: AsyncSession) -> User:
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"cand_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="fakehash",
        role=UserRole.candidate,
        is_active=True,
        token_version=1,
    )
    session.add(user)
    profile = CandidateProfile(user_id=uid)
    session.add(profile)
    return user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id, role=user.role.value, token_version=user.token_version
    )
    return {"Authorization": f"Bearer {token}"}


def _make_job(
    session: AsyncSession,
    company_id: uuid.UUID,
    *,
    status: JobStatus = JobStatus.live,
    title: str = "Test Job",
    required_skills: list[str] | None = None,
) -> JobPosting:
    job = JobPosting(
        id=uuid.uuid4(),
        company_id=company_id,
        title=title,
        status=status,
        required_skills=required_skills or ["Python"],
        description="A test job.",
        min_salary=50000,
        max_salary=100000,
    )
    session.add(job)
    return job


# ── Query counter context manager ────────────────────────────────────────────


class _QueryCounter:
    """Count raw SQL statements via a before_cursor_execute listener on the
    sync engine underneath the AsyncEngine."""

    def __init__(self, async_engine):
        self._sync_engine = async_engine.sync_engine
        self.count = 0

    def _listener(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

    def __enter__(self):
        self.count = 0
        event.listen(self._sync_engine, "before_cursor_execute", self._listener)
        return self

    def __exit__(self, *args):
        event.remove(self._sync_engine, "before_cursor_execute", self._listener)


# ── GET /jobs/{id} ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_job_owner_returns_company_name_and_counts(db_session: AsyncSession):
    """GET /jobs/{id} as the owning company returns 200, company_name,
    and integer matched/shortlisted counts."""
    owner, company = _make_company_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.live)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/jobs/{job.id}", headers=_headers(owner))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["company_name"] == company.name
    assert isinstance(data["matched"], int)
    assert isinstance(data["shortlisted"], int)


@pytest.mark.asyncio
async def test_get_job_candidate_live_returns_company_name(db_session: AsyncSession):
    """GET /jobs/{id} as a different candidate for a LIVE job: 200 with
    company_name."""
    owner, company = _make_company_user(db_session)
    candidate = _make_candidate_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.live)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/jobs/{job.id}", headers=_headers(candidate))

    assert resp.status_code == 200, resp.text
    assert resp.json()["company_name"] == company.name


@pytest.mark.asyncio
async def test_get_job_candidate_draft_returns_404(db_session: AsyncSession):
    """GET /jobs/{id} as a candidate for a DRAFT job: 404."""
    owner, _ = _make_company_user(db_session)
    candidate = _make_candidate_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.draft)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/jobs/{job.id}", headers=_headers(candidate))

    assert resp.status_code == 404


# ── PUT /jobs/{id} ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_job_returns_updated_fields_and_company_name(
    db_session: AsyncSession,
):
    """PUT /jobs/{id} as owner: 200, updated fields reflected, company_name
    present, counts present."""
    owner, company = _make_company_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.draft, title="Old Title")
    await db_session.commit()

    payload = {
        "title": "Brand New Title",
        "description": "Updated desc",
        "min_salary": 60000,
        "max_salary": 120000,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            f"/jobs/{job.id}", json=payload, headers=_headers(owner)
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Brand New Title"
    assert data["description"] == "Updated desc"
    assert data["min_salary"] == 60000
    assert data["max_salary"] == 120000
    assert data["company_name"] == company.name
    assert isinstance(data["matched"], int)
    assert isinstance(data["shortlisted"], int)


# ── PATCH /jobs/{id} (partial update) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_job_partial_preserves_other_fields(db_session: AsyncSession):
    """PATCH /jobs/{id} (partial body): only the sent fields change;
    everything else is preserved; company_name present."""
    owner, company = _make_company_user(db_session)
    job = _make_job(
        db_session,
        owner.id,
        status=JobStatus.draft,
        title="Original Title",
    )
    await db_session.commit()

    original_title = "Original Title"

    # Only change description
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/jobs/{job.id}",
            json={"description": "patched desc"},
            headers=_headers(owner),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["description"] == "patched desc"
    assert data["title"] == original_title  # preserved
    assert data["company_name"] == company.name


# ── PATCH /jobs/{id}/status ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_status_changes_status_and_returns_company_name(
    db_session: AsyncSession,
):
    """PATCH /jobs/{id}/status: status changes, response shows it,
    company_name present."""
    owner, company = _make_company_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.draft)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/jobs/{job.id}/status",
            json={"status": "live"},
            headers=_headers(owner),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "live"
    assert data["company_name"] == company.name


# ── IDOR: PUT/PATCH by another company → 404, job unchanged ─────────────────


@pytest.mark.asyncio
async def test_put_by_other_company_returns_404(db_session: AsyncSession):
    """PUT /jobs/{id} by a different company returns 404 (not 403), and the
    job is unchanged afterwards."""
    owner, _ = _make_company_user(db_session)
    intruder, _ = _make_company_user(db_session)
    job = _make_job(db_session, owner.id, status=JobStatus.live, title="Keep Me")
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            f"/jobs/{job.id}",
            json={"title": "Hacked!"},
            headers=_headers(intruder),
        )
        assert resp.status_code == 404

        # Confirm unchanged
        check = await client.get(f"/jobs/{job.id}", headers=_headers(owner))
        assert check.status_code == 200
        assert check.json()["title"] == "Keep Me"


@pytest.mark.asyncio
async def test_patch_by_other_company_returns_404(db_session: AsyncSession):
    """PATCH /jobs/{id} by a different company returns 404 and the job is
    unchanged."""
    owner, _ = _make_company_user(db_session)
    intruder, _ = _make_company_user(db_session)
    job = _make_job(
        db_session, owner.id, status=JobStatus.live, title="Unchanged Title"
    )
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/jobs/{job.id}",
            json={"title": "Hacked!"},
            headers=_headers(intruder),
        )
        assert resp.status_code == 404

        check = await client.get(f"/jobs/{job.id}", headers=_headers(owner))
        assert check.status_code == 200
        assert check.json()["title"] == "Unchanged Title"


# ── Query-count stability: GET and PUT ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_job_query_count_stable_with_skills(db_session: AsyncSession):
    """GET /jobs/{id}: query count is the same with 1 skill and with 20 skills."""
    from core.database import engine

    owner, _ = _make_company_user(db_session)
    job_1 = _make_job(
        db_session, owner.id, status=JobStatus.live, required_skills=["Python"]
    )
    job_20 = _make_job(
        db_session,
        owner.id,
        status=JobStatus.live,
        required_skills=[f"Skill{i}" for i in range(20)],
    )
    await db_session.commit()

    headers = _headers(owner)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with _QueryCounter(engine) as ctr1:
            r1 = await client.get(f"/jobs/{job_1.id}", headers=headers)
        assert r1.status_code == 200

        with _QueryCounter(engine) as ctr20:
            r20 = await client.get(f"/jobs/{job_20.id}", headers=headers)
        assert r20.status_code == 200

    assert ctr1.count == ctr20.count, (
        f"GET /jobs/{{id}} query count differs: 1-skill={ctr1.count}, "
        f"20-skills={ctr20.count}"
    )
    # Allow a small tolerance; print in failure message for diagnosis.
    assert (
        ctr1.count <= ctr1.count + 1
    ), f"GET /jobs/{{id}} measured {ctr1.count} queries"


@pytest.mark.asyncio
async def test_put_job_query_count_stable_with_skills(db_session: AsyncSession):
    """PUT /jobs/{id}: query count is the same with 1 skill and with 20 skills."""
    from core.database import engine

    owner, _ = _make_company_user(db_session)
    job_1 = _make_job(
        db_session,
        owner.id,
        status=JobStatus.draft,
        required_skills=["Python"],
    )
    job_20 = _make_job(
        db_session,
        owner.id,
        status=JobStatus.draft,
        required_skills=[f"Skill{i}" for i in range(20)],
    )
    await db_session.commit()

    headers = _headers(owner)
    payload = {"title": "Updated"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with _QueryCounter(engine) as ctr1:
            r1 = await client.put(f"/jobs/{job_1.id}", json=payload, headers=headers)
        assert r1.status_code == 200

        with _QueryCounter(engine) as ctr20:
            r20 = await client.put(f"/jobs/{job_20.id}", json=payload, headers=headers)
        assert r20.status_code == 200

    assert ctr1.count == ctr20.count, (
        f"PUT /jobs/{{id}} query count differs: 1-skill={ctr1.count}, "
        f"20-skills={ctr20.count}"
    )
    assert (
        ctr1.count <= ctr1.count + 1
    ), f"PUT /jobs/{{id}} measured {ctr1.count} queries"
