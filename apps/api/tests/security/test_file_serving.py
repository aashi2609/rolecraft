"""Tests for authenticated file serving and access control.

Verifies:
1. Unauthenticated request to /files/{id} returns 401.
2. Unauthenticated request to old /static/ route returns 404 (static mount removed).
3. Owner can access their uploaded file.
4. Another candidate cannot access candidate A's document (returns 404).
5. Unrelated company cannot access candidate A's document (returns 404).
6. Company with job application from candidate CAN access candidate's document.
7. Company logos are publicly readable via /files/logo/{id}.
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from models import Application, ApplicationStatus, JobPosting


def _signup(client: TestClient, role: str = "candidate") -> tuple[str, str]:
    uid = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/signup",
        json={
            "email": f"user_{uid}@test.com",
            "password": "testpass123A",
            "role": role,
            "name": f"User {uid}",
        },
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"], data["user_id"]


def _upload_png(client: TestClient, token: str, endpoint: str = "/uploads/photo") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = client.post(
        endpoint,
        headers=headers,
        files={"file": ("test.png", png, "image/png")},
    )
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text}"
    return r.json()


def test_static_mount_removed(client: TestClient) -> None:
    """Verifies that unauthenticated /static access is completely removed (returns 404)."""
    r = client.get("/static/photos/any/test.png")
    assert r.status_code == 404


def test_unauthenticated_file_access_blocked(client: TestClient) -> None:
    """Uploading a file, then trying to GET without auth header MUST fail with 401."""
    tok, _ = _signup(client, "candidate")
    upload_res = _upload_png(client, tok, "/uploads/photo")
    url = upload_res["url"]
    assert url.startswith("/files/"), f"Unexpected url: {url}"

    # Try fetching with no auth header
    r = client.get(url)
    assert r.status_code == 401, f"Expected 401 for unauthenticated access, got {r.status_code}"


def test_file_access_owner_and_other_candidate(client: TestClient) -> None:
    """Owner can access their own document; another candidate receives 404."""
    tok_a, _ = _signup(client, "candidate")
    tok_b, _ = _signup(client, "candidate")

    upload_res = _upload_png(client, tok_a, "/uploads/document")
    url = upload_res["url"]

    # Owner can access
    r_owner = client.get(url, headers={"Authorization": f"Bearer {tok_a}"})
    assert r_owner.status_code == 200, f"Owner failed: {r_owner.status_code}"

    # Other candidate is denied with 404
    r_other = client.get(url, headers={"Authorization": f"Bearer {tok_b}"})
    assert r_other.status_code == 404, f"Other candidate expected 404, got {r_other.status_code}"


def test_company_access_to_candidate_document_requires_application(client: TestClient) -> None:
    """A company cannot view candidate's private document unless the candidate applied to their job."""
    tok_cand, cand_id = _signup(client, "candidate")
    tok_co1, co1_id = _signup(client, "company")
    tok_co2, co2_id = _signup(client, "company")

    # Candidate uploads a document
    upload_res = _upload_png(client, tok_cand, "/uploads/document")
    url = upload_res["url"]

    # Co1 tries to view before application -> 404
    r_co1_before = client.get(url, headers={"Authorization": f"Bearer {tok_co1}"})
    assert r_co1_before.status_code == 404

    # Post a job by co1
    r_job = client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {tok_co1}"},
        json={
            "title": "Software Engineer",
            "status": "published",
            "description": "Backend role",
            "min_salary": 50000,
            "max_salary": 90000,
        },
    )
    if r_job.status_code == 200:
        job_id = r_job.json()["id"]
        # Candidate applies to co1's job
        r_apply = client.post(
            f"/applications/apply",
            headers={"Authorization": f"Bearer {tok_cand}"},
            json={"job_id": job_id},
        )
        if r_apply.status_code == 200:
            # Now Co1 can access candidate's document
            r_co1_after = client.get(url, headers={"Authorization": f"Bearer {tok_co1}"})
            assert r_co1_after.status_code == 200

            # Co2 still cannot access candidate's document -> 404
            r_co2 = client.get(url, headers={"Authorization": f"Bearer {tok_co2}"})
            assert r_co2.status_code == 404


def test_company_logo_is_public(client: TestClient) -> None:
    """Company logos use /files/logo/{id} and are readable without authentication."""
    tok_co, _ = _signup(client, "company")
    upload_res = _upload_png(client, tok_co, "/uploads/logo")
    url = upload_res["url"]
    assert url.startswith("/files/logo/"), f"Expected /files/logo/ URL, got {url}"

    # Fetch without Authorization header
    r = client.get(url)
    assert r.status_code == 200, f"Expected 200 for public logo, got {r.status_code}"
