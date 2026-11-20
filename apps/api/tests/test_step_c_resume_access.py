"""Step C: company resume access — route x role matrix.

Rule: a company sees ONLY the resume submitted on an application to its
job. Owner candidate and admin: 200. Matching company: 200. Everyone
else: 404 (anonymous: 401).
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from core.security import create_access_token
from main import app
from models import (
    Application,
    Resume,
    User,
    UserRole,
)


def _resume(candidate_id, **kw) -> Resume:
    return Resume(
        id=kw.pop("id", uuid.uuid4()),
        candidate_id=candidate_id,
        target_vertical=kw.pop("target_vertical", "Backend Engineer"),
        content=kw.pop("content", {"summary": "Step C test resume"}),
        version=1,
        **kw,
    )


@pytest_asyncio.fixture
async def resume_pair(db_session, candidate_user):
    """Two resumes for the candidate: r1 (applied) and r2 (not applied)."""
    r1 = _resume(candidate_user.id)
    r2 = _resume(candidate_user.id, target_vertical="Data Engineer")
    db_session.add_all([r1, r2])
    await db_session.commit()
    return r1, r2


@pytest_asyncio.fixture
async def applied_resume(db_session, candidate_user, company_user, resume_pair, make_job):
    """r1 applied to company_user's job; returns (resume, application)."""
    r1, _ = resume_pair
    job = await make_job(company_id=company_user.id)
    app_row = Application(
        id=uuid.uuid4(),
        candidate_id=candidate_user.id,
        job_id=job.id,
        resume_id=r1.id,
        status="applied",
    )
    db_session.add(app_row)
    await db_session.commit()
    return r1, app_row


async def _client_for(user: User) -> AsyncClient:
    token = create_access_token(user_id=user.id, role=user.role.value)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ── GET /resumes/{id}/pdf ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pdf_owner_candidate_200(db_session, candidate_user, applied_resume):
    r1, _ = applied_resume
    async with await _client_for(candidate_user) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "no-store" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_pdf_other_candidate_404(db_session, applied_resume, make_job):
    r1, _ = applied_resume
    other = User(
        id=uuid.uuid4(),
        email=f"oc_{uuid.uuid4().hex[:6]}@t.com",
        password_hash="x",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()
    async with await _client_for(other) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_pdf_matching_company_200(db_session, company_user, applied_resume):
    r1, _ = applied_resume
    async with await _client_for(company_user) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pdf_company_different_resume_404(
    db_session, company_user, applied_resume, resume_pair
):
    """Company applied with r1 — must NOT get r2 (same candidate)."""
    _, r2 = resume_pair
    async with await _client_for(company_user) as c:
        r = await c.get(f"/resumes/{r2.id}/pdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_pdf_unrelated_company_404(db_session, other_company_user, applied_resume):
    r1, _ = applied_resume
    async with await _client_for(other_company_user) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_pdf_admin_200(db_session, admin_user, applied_resume):
    r1, _ = applied_resume
    async with await _client_for(admin_user) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_pdf_anonymous_401(db_session, applied_resume):
    r1, _ = applied_resume
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_pdf_deactivated_company_401(db_session, company_user, applied_resume):
    company_user.is_active = False
    await db_session.commit()
    r1, _ = applied_resume
    async with await _client_for(company_user) as c:
        r = await c.get(f"/resumes/{r1.id}/pdf")
    assert r.status_code == 401


# ── GET /candidates/{id}/resume.pdf ──────────────────────────────────────


@pytest.mark.asyncio
async def test_candidate_pdf_matching_company_200(
    db_session, company_user, candidate_user, applied_resume
):
    async with await _client_for(company_user) as c:
        r = await c.get(f"/candidates/{candidate_user.id}/resume.pdf")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_candidate_pdf_unrelated_company_404(
    db_session, other_company_user, candidate_user, applied_resume
):
    async with await _client_for(other_company_user) as c:
        r = await c.get(f"/candidates/{candidate_user.id}/resume.pdf")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_candidate_pdf_company_no_application_404(
    db_session, company_user, candidate_user, resume_pair
):
    """Company with NO application must not get the default/latest resume."""
    async with await _client_for(company_user) as c:
        r = await c.get(f"/candidates/{candidate_user.id}/resume.pdf")
    assert r.status_code == 404
