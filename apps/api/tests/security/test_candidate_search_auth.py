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
    from services.plan_limits import get_user_plan
    from sqlalchemy import select
    from models import Subscription
    
    # Grant paid plan to company (using growth tier which is in _ALLOWED_SEARCH_COMPANY_PLANS)
    subscription = await grant_plan(
        user_id=company_user.id,
        plan_tier=PlanTier.growth,
        status=SubscriptionStatus.active,
    )
    await db_session.commit()
    
    # DEBUG: Print subscription row
    sub_row = await db_session.scalar(select(Subscription).where(Subscription.user_id == company_user.id))
    print(f"DEBUG Subscription row: id={sub_row.id}, user_id={sub_row.user_id}, plan_tier={sub_row.plan_tier}, status={sub_row.status}")
    
    # DEBUG: Print get_user_plan result
    plan_result = await get_user_plan(company_user.id, db_session)
    print(f"DEBUG get_user_plan result: {plan_result}")
    
    # Create AsyncClient with company token
    company_token = create_access_token(user_id=company_user.id, role="company")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {company_token}"
        
        r = await client.get("/candidates/search")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Assert exact key allowlist for each candidate result
        allowed_keys = {
            "id", "name", "title", "experience_years", "location", "skills",
            "match_percent", "education", "expected_salary_lpa", "notice_period_days",
            "photo_url", "rationale", "rationale_source"
        }
        
        # PII fields that should NOT be in candidate search results
        forbidden_pii_keys = {
            "email", "phone", "address", "ssn", "dob", "date_of_birth",
            "bank_account", "credit_card", "password", "secret",
        }
        
        if "results" in data:
            for candidate in data["results"]:
                actual_keys = set(candidate.keys())
                # All actual keys must be in allowed list
                assert actual_keys.issubset(allowed_keys), (
                    f"Unexpected keys in result: {actual_keys - allowed_keys}"
                )
                # No forbidden PII keys
                assert not actual_keys.intersection(forbidden_pii_keys), (
                    f"PII keys found: {actual_keys.intersection(forbidden_pii_keys)}"
                )
        elif isinstance(data, list):
            for candidate in data:
                actual_keys = set(candidate.keys())
                # All actual keys must be in allowed list
                assert actual_keys.issubset(allowed_keys), (
                    f"Unexpected keys in result: {actual_keys - allowed_keys}"
                )
                # No forbidden PII keys
                assert not actual_keys.intersection(forbidden_pii_keys), (
                    f"PII keys found: {actual_keys.intersection(forbidden_pii_keys)}"
                )


def test_search_admin_allowed(client: TestClient, admin_user) -> None:
    """Admin role is allowed to search candidates without requiring a company subscription."""
    admin_token = create_access_token(user_id=admin_user.id, role="admin")

    r = client.get(
        "/candidates/search",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
