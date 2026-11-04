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

import pytest
from fastapi.testclient import TestClient

from core.security import create_access_token
from models import PlanTier, SubscriptionStatus


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


def test_search_unpaid_company_returns_403(client: TestClient, unpaid_company_user) -> None:
    """A company user whose subscription is cancelled / inactive gets 403 with upgrade message."""
    unpaid_token = create_access_token(user_id=unpaid_company_user.id, role="company")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {unpaid_token}"},
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    data = r.json()
    detail = data.get("detail", "").lower()
    assert "subscription" in detail or "upgrade" in detail, (
        f"Expected upgrade message, got {detail}"
    )


@pytest.mark.asyncio
async def test_search_paid_company_returns_200_and_no_pii_keys(
    company_user, grant_plan, db_session
) -> None:
    """Paid company returns 200 with no PII in results.
    
    Uses grant_plan fixture to activate subscription, then verifies search works.
    """
    from httpx import AsyncClient, ASGITransport
    from core.security import create_access_token
    from main import app
    
    # Grant paid plan to company
    subscription = await grant_plan(
        user_id=company_user.id,
        plan_tier=PlanTier.complete,
        status=SubscriptionStatus.active,
    )
    await db_session.commit()
    
    # Create AsyncClient with company token
    company_token = create_access_token(user_id=company_user.id, role="company")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {company_token}"
        
        r = await client.get("/candidates/search")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify no PII keys in results
        # PII fields that should NOT be in candidate search results
        forbidden_pii_keys = {
            "email", "phone", "address", "ssn", "dob", "date_of_birth",
            "bank_account", "credit_card", "password", "secret",
        }
        
        if "results" in data:
            for candidate in data["results"]:
                for key in forbidden_pii_keys:
                    assert key.lower() not in {k.lower() for k in candidate.keys()}, (
                        f"PII key '{key}' found in candidate search results"
                    )
        elif isinstance(data, list):
            for candidate in data:
                for key in forbidden_pii_keys:
                    assert key.lower() not in {k.lower() for k in candidate.keys()}, (
                        f"PII key '{key}' found in candidate search results"
                    )


def test_search_admin_allowed(client: TestClient, admin_user) -> None:
    """Admin role is allowed to search candidates without requiring a company subscription."""
    admin_token = create_access_token(user_id=admin_user.id, role="admin")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
