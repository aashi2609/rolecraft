"""Tests for Candidate Search Authentication, Authorization, and PII protection (Pass 1B).

Verification requirements:
- No token returns 401
- Candidate token returns 403
- Unpaid company returns 403 (with upgrade message)
- Paid company returns 200 with no PII fields in the payload (assert on actual keys)
- Admin role is allowed to search candidates
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient

from core.security import create_access_token


def _signup(client: TestClient, role: str = "candidate") -> tuple[str, str]:
    uid = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/signup",
        json={
            "email": f"cs_{uid}@test.com",
            "password": "testpass123A",
            "role": role,
            "name": f"User {uid}",
        },
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"], data["user_id"]


def test_search_unauthenticated_returns_401(client: TestClient) -> None:
    """GET /candidates/search without Authorization header must return 401."""
    r = client.get("/candidates/search")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


def test_search_candidate_token_returns_403(client: TestClient) -> None:
    """GET /candidates/search with candidate role token must return 403."""
    cand_token, _ = _signup(client, role="candidate")
    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    assert "Forbidden" in r.text or "restricted" in r.text.lower()


def test_search_unpaid_company_returns_403(client: TestClient) -> None:
    """A company user whose subscription is cancelled / inactive gets 403 with upgrade message."""
    # User 5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1 is a company user with SubscriptionStatus.cancelled in DB
    cancelled_company_id = uuid.UUID("5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1")
    unpaid_token = create_access_token(user_id=cancelled_company_id, role="company")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {unpaid_token}"},
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    data = r.json()
    detail = data.get("detail", "").lower()
    assert "subscription" in detail or "upgrade" in detail, f"Expected upgrade message, got {detail}"


def test_search_paid_company_returns_200_and_no_pii_keys(client: TestClient) -> None:
    """Paid company returns 200. Every item in the response list must NOT contain any PII fields."""
    company_token, _ = _signup(client, role="company")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {company_token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0, "Expected non-empty search results for verification"

    # Forbidden PII keys
    forbidden_keys = {
        "email",
        "phone",
        "mobile",
        "phone_number",
        "present_address",
        "permanent_address",
        "address",
        "dob",
        "date_of_birth",
        "annual_family_income",
        "family",
        "income",
    }

    # Assert on actual keys returned in payload
    for item in data:
        present_forbidden = forbidden_keys.intersection(item.keys())
        assert not present_forbidden, f"PII fields leaked in candidate search payload: {present_forbidden}"


def test_search_admin_allowed(client: TestClient) -> None:
    """Admin role is allowed to search candidates without requiring a company subscription."""
    admin_id = uuid.UUID("b55c77e8-1a01-4f9c-a1ff-4568879121c7")
    admin_token = create_access_token(user_id=admin_id, role="admin")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
