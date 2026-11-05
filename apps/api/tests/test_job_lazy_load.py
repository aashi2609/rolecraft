"""
Tests for enrich_job() call sites to ensure no lazy loading in async context.

Rules:
- All enrich_job() calls must receive company= with pre-loaded data
- No relationship access (job.company, etc.) after plain select without eager load
- Query count must not grow with company or skill relationships
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from main import app
from models import Company, JobPosting, JobStatus, JobType, User, UserRole


class QueryCounter:
    """Context manager to count SQL queries during a block."""

    def __init__(self):
        self.count = 0
        self._listener_added = False

    def __enter__(self):
        self.count = 0

        def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            self.count += 1

        # Attach to the sync engine's pool
        event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
        self._listener_added = True
        self._callback = _before_cursor_execute
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._listener_added:
            event.remove(Engine, "before_cursor_execute", self._callback)


@pytest.mark.asyncio
async def test_job_endpoints_do_not_lazy_load_company(db_session: AsyncSession):
    """
    GET, PUT, PATCH /jobs/{id} must eager-load company and pass it to enrich_job.
    Response must include company_name and matched/shortlisted counts.
    Query count for GET must not grow with company or skill count.
    """
    # 1. Create company user and company profile
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
        name="Test Corp Inc",
        industry="Technology",
        website="https://testcorp.example",
    )
    db_session.add(company_profile)

    # 2. Create a job
    job_id = uuid.uuid4()
    job = JobPosting(
        id=job_id,
        company_id=company_id,
        title="Senior Backend Engineer",
        description="Build scalable systems",
        status=JobStatus.live,
        job_type=JobType.remote,
        required_skills=["Python", "PostgreSQL", "Docker"],
        location="Remote",
    )
    db_session.add(job)
    await db_session.commit()

    # 3. Create another candidate user for "GET as different user" test
    candidate_id = uuid.uuid4()
    candidate_user = User(
        id=candidate_id,
        email=f"candidate_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
        role=UserRole.candidate,
        is_active=True,
    )
    db_session.add(candidate_user)
    await db_session.commit()

    company_token = create_access_token(user_id=company_id, role="company", token_version=1)
    candidate_token = create_access_token(user_id=candidate_id, role="candidate", token_version=1)
    company_headers = {"Authorization": f"Bearer {company_token}"}
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TEST 1: GET /jobs/{id} as owning company
        resp = await client.get(f"/jobs/{job_id}", headers=company_headers)
        assert resp.status_code == 200, f"GET failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data["id"] == str(job_id)
        assert data["company_name"] == "Test Corp Inc", (
            f"company_name missing or wrong: {data.get('company_name')}"
        )
        assert "matched" in data, "matched count missing"
        assert "shortlisted" in data, "shortlisted count missing"
        assert data["matched"] == 0  # No applications yet
        assert data["shortlisted"] == 0

        # TEST 2: GET /jobs/{id} as different user (candidate) for live job
        resp = await client.get(f"/jobs/{job_id}", headers=candidate_headers)
        assert resp.status_code == 200, f"GET as candidate failed: {resp.status_code} {resp.text}"
        candidate_data = resp.json()
        assert candidate_data["id"] == str(job_id)
        assert candidate_data["company_name"] == "Test Corp Inc", (
            "company_name missing for candidate GET"
        )

        # TEST 3: PUT /jobs/{id} - update job and check response
        update_payload = {
            "title": "Staff Backend Engineer",
            "description": "Build highly scalable systems",
            "required_skills": ["Python", "PostgreSQL", "Docker", "Kubernetes"],
        }
        resp = await client.put(f"/jobs/{job_id}", json=update_payload, headers=company_headers)
        assert resp.status_code == 200, f"PUT failed: {resp.status_code} {resp.text}"
        put_data = resp.json()
        assert put_data["id"] == str(job_id)
        assert put_data["title"] == "Staff Backend Engineer", "PUT response title not updated"
        assert put_data["description"] == "Build highly scalable systems", (
            "PUT response description not updated"
        )
        assert put_data["company_name"] == "Test Corp Inc", "company_name missing after PUT"
        assert "matched" in put_data, "matched missing after PUT"
        assert "shortlisted" in put_data, "shortlisted missing after PUT"

        # TEST 4: PATCH /jobs/{id}/status - change status and check response
        patch_payload = {"status": "draft"}
        resp = await client.patch(f"/jobs/{job_id}/status", json=patch_payload, headers=company_headers)
        assert resp.status_code == 200, f"PATCH /status failed: {resp.status_code} {resp.text}"
        patch_data = resp.json()
        assert patch_data["id"] == str(job_id)
        assert patch_data["status"] == "draft", "PATCH response status not updated"
        assert patch_data["company_name"] == "Test Corp Inc", "company_name missing after PATCH"
        assert "matched" in patch_data, "matched missing after PATCH"
        assert "shortlisted" in patch_data, "shortlisted missing after PATCH"

        # TEST 5: Query count for GET /jobs/{id} must not grow with company/skill count
        # Change job back to live for this test
        await client.patch(
            f"/jobs/{job_id}/status", json={"status": "live"}, headers=company_headers
        )

        # Measure queries for GET request
        with QueryCounter() as counter:
            resp = await client.get(f"/jobs/{job_id}", headers=company_headers)
            assert resp.status_code == 200
            initial_query_count = counter.count

        # Add more skills and check query count doesn't increase
        update_with_more_skills = {
            "required_skills": ["Python", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka"]
        }
        await client.put(f"/jobs/{job_id}", json=update_with_more_skills, headers=company_headers)

        with QueryCounter() as counter:
            resp = await client.get(f"/jobs/{job_id}", headers=company_headers)
            assert resp.status_code == 200
            final_query_count = counter.count

        # Query count should not increase with more skills
        assert final_query_count <= initial_query_count + 1, (
            f"Query count grew from {initial_query_count} to {final_query_count} "
            f"when skills increased. This indicates N+1 or lazy loading."
        )

        # Assert a reasonable ceiling (should be ~3-5 queries max for simple GET)
        # 1: get user, 2: get job with company eager-load, maybe 3: stats query
        assert final_query_count <= 6, (
            f"Query count {final_query_count} exceeds ceiling of 6. "
            f"GET /jobs/{{id}} should use eager-loading and not have N+1 issues."
        )


@pytest.mark.asyncio
async def test_patch_full_job_body(db_session: AsyncSession):
    """
    Test PATCH /jobs/{id} (not /status) with full job body.
    Response must reflect updated values and include company_name + counts.
    """
    # 1. Create company user and company profile
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
        name="Patch Test Corp",
    )
    db_session.add(company_profile)

    # 2. Create a job
    job_id = uuid.uuid4()
    job = JobPosting(
        id=job_id,
        company_id=company_id,
        title="Original Title",
        description="Original description",
        status=JobStatus.draft,
        job_type=JobType.remote,
    )
    db_session.add(job)
    await db_session.commit()

    company_token = create_access_token(user_id=company_id, role="company", token_version=1)
    company_headers = {"Authorization": f"Bearer {company_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # PATCH /jobs/{id} (full update endpoint)
        patch_payload = {
            "title": "Patched Title",
            "status": "live",
        }
        resp = await client.patch(f"/jobs/{job_id}", json=patch_payload, headers=company_headers)
        assert resp.status_code == 200, f"PATCH /jobs/{{id}} failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data["id"] == str(job_id)
        assert data["title"] == "Patched Title", "PATCH response title not updated"
        assert data["status"] == "live", "PATCH response status not updated"
        assert data["company_name"] == "Patch Test Corp", "company_name missing after PATCH"
        assert "matched" in data, "matched missing after PATCH"
        assert "shortlisted" in data, "shortlisted missing after PATCH"
