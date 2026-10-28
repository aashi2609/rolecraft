"""Tests for 4A: GET /jobs/hidden route ordering, hide, unhide, and hidden job filtering."""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from models import CandidateProfile, Company, JobPosting, JobStatus, JobType, User, UserRole
from core.security import create_access_token


@pytest.mark.asyncio
async def test_jobs_hidden_route_and_filtering(db_session: AsyncSession):
    # 1. Create a company user, company profile, and a job posting
    company_id = uuid.uuid4()
    company_user = User(
        id=company_id,
        email=f"company_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        role=UserRole.company,
        is_active=True,
    )
    db_session.add(company_user)

    company_profile = Company(
        user_id=company_id,
        name="Acme 4A Test Corp",
    )
    db_session.add(company_profile)

    job_id = uuid.uuid4()
    job = JobPosting(
        id=job_id,
        company_id=company_id,
        title="Software Engineer Test 4A",
        status=JobStatus.live,
        job_type=JobType.remote,
    )
    db_session.add(job)

    # 2. Create a candidate user and candidate profile (required for hidden_jobs FK)
    candidate_id = uuid.uuid4()
    candidate_user = User(
        id=candidate_id,
        email=f"candidate_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(candidate_user)

    candidate_profile = CandidateProfile(
        user_id=candidate_id,
        career_level="mid",
    )
    db_session.add(candidate_profile)
    await db_session.commit()

    token = create_access_token(user_id=candidate_id, role="candidate", token_version=1)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 3. Initially, GET /jobs/hidden returns empty list
        resp = await client.get("/jobs/hidden", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "job_ids" in data
        assert str(job_id) not in data["job_ids"]

        # 4. Job is present in GET /jobs
        resp = await client.get("/jobs", headers=headers)
        assert resp.status_code == 200
        jobs_list = resp.json()
        job_ids_returned = [j["id"] for j in jobs_list]
        assert str(job_id) in job_ids_returned

        # 5. Hide the job: POST /jobs/{job_id}/hide
        resp = await client.post(f"/jobs/{job_id}/hide", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json() == {"status": "ok"}

        # 6. GET /jobs/hidden now returns the hidden job ID
        resp = await client.get("/jobs/hidden", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert str(job_id) in data["job_ids"]

        # 7. GET /jobs for this candidate no longer includes the hidden job
        resp = await client.get("/jobs", headers=headers)
        assert resp.status_code == 200
        jobs_list = resp.json()
        job_ids_returned = [j["id"] for j in jobs_list]
        assert str(job_id) not in job_ids_returned

        # 8. GET /jobs/{real-uuid} still works for candidate
        resp = await client.get(f"/jobs/{job_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(job_id)

        # 9. Unhide the job: DELETE /jobs/{job_id}/hide
        resp = await client.delete(f"/jobs/{job_id}/hide", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json() == {"status": "ok"}

        # 10. GET /jobs/hidden no longer returns the job
        resp = await client.get("/jobs/hidden", headers=headers)
        assert resp.status_code == 200
        assert str(job_id) not in resp.json()["job_ids"]

        # 11. GET /jobs returns the job again
        resp = await client.get("/jobs", headers=headers)
        assert resp.status_code == 200
        assert str(job_id) in [j["id"] for j in resp.json()]
