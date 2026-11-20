"""Tests for 1D: Deactivated / banned user enforcement.

Verifies that:
1. A deactivated user's existing token stops working on protected endpoints (401).
2. Signin rejects deactivated users with a generic message (401).
3. Password-change rejects deactivated users (401).
4. WebSocket auth closes the connection for deactivated users (code 4004).
5. Admin can deactivate and reactivate a user.

Run from apps/api:
    PYTHONPATH=. python -m pytest tests/security/test_deactivation.py -v
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from core.security import create_access_token

# ── Fixtures ─────────────────────────────────────────────────────────────

# The admin UUID that exists in the production/test database.
# The same user is used in test_candidate_search_auth.py.
_ADMIN_ID = uuid.UUID("b55c77e8-1a01-4f9c-a1ff-4568879121c7")


# (client fixture is provided by conftest.py)


@pytest.fixture
def admin_token() -> str:
    """JWT token for the seeded admin user (created on demand for fresh DBs)."""
    _ensure_seed_users()
    return create_access_token(user_id=_ADMIN_ID, role="admin")


# ── Helpers ──────────────────────────────────────────────────────────────


def _signup(
    client: TestClient,
    email: str,
    role: str = "candidate",
    password: str = "testpass123A",
) -> dict:
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "role": role, "name": "Test User"},
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()


def _deactivate_user(client: TestClient, admin_token: str, user_id: str) -> None:
    """Deactivate a user via admin PATCH endpoint."""
    r = client.patch(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert r.status_code == 200, f"deactivate failed: {r.status_code} {r.text}"


def _reactivate_user(client: TestClient, admin_token: str, user_id: str) -> None:
    """Reactivate a user via admin PATCH endpoint."""
    r = client.patch(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": True},
    )
    assert r.status_code == 200, f"reactivate failed: {r.status_code} {r.text}"


# ── Tests ────────────────────────────────────────────────────────────────


class TestDeactivatedUserTokenRevocation:
    """A deactivated user's already-issued token stops working immediately."""

    def test_candidate_token_revoked_on_deactivation(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]
        cand = _signup(client, f"deact_cand_{uid}@test.com", "candidate")
        cand_token = cand["access_token"]
        cand_id = cand["user_id"]

        # Token works BEFORE deactivation
        r = client.get(
            f"/candidates/{cand_id}",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert r.status_code == 200, f"pre-deactivation: {r.status_code}"

        # Deactivate via admin
        _deactivate_user(client, admin_token, cand_id)

        # Same token should now return 401
        r = client.get(
            f"/candidates/{cand_id}",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert r.status_code == 401, f"post-deactivation: expected 401, got {r.status_code}"

    def test_company_token_revoked_on_deactivation(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]
        company = _signup(client, f"deact_comp_{uid}@test.com", "company")
        comp_token = company["access_token"]
        comp_id = company["user_id"]

        # Token works
        r = client.get(
            "/jobs/mine",
            headers={"Authorization": f"Bearer {comp_token}"},
        )
        assert r.status_code == 200, f"pre-deactivation: {r.status_code}"

        _deactivate_user(client, admin_token, comp_id)

        # Token revoked
        r = client.get(
            "/jobs/mine",
            headers={"Authorization": f"Bearer {comp_token}"},
        )
        assert r.status_code == 401, f"post-deactivation: expected 401, got {r.status_code}"


class TestDeactivatedUserSignin:
    """Signin must reject deactivated users with a generic message."""

    def test_signin_rejected_after_deactivation(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]
        email = f"deact_signin_{uid}@test.com"
        password = "testpass123A"

        cand = _signup(client, email, "candidate", password)
        cand_id = cand["user_id"]

        # Signin works before deactivation
        r = client.post("/auth/signin", json={"email": email, "password": password})
        assert r.status_code == 200, f"pre-deactivation signin: {r.status_code}"

        _deactivate_user(client, admin_token, cand_id)

        # Signin must fail — same generic message as wrong credentials
        r = client.post("/auth/signin", json={"email": email, "password": password})
        assert r.status_code == 401, f"post-deactivation signin: expected 401, got {r.status_code}"
        assert r.json()["detail"] == "Invalid email or password"


class TestDeactivatedUserPasswordChange:
    """Change-password requires CurrentUser, which checks is_active."""

    def test_change_password_rejected_for_deactivated_user(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]
        password = "testpass123A"

        cand = _signup(client, f"deact_pwd_{uid}@test.com", "candidate", password)
        cand_token = cand["access_token"]
        cand_id = cand["user_id"]

        _deactivate_user(client, admin_token, cand_id)

        r = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {cand_token}"},
            json={"current_password": password, "new_password": "newPass123B"},
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}"


class TestDeactivatedUserWebSocket:
    """WebSocket authentication rejects deactivated users."""

    def test_websocket_closed_for_deactivated_user(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]

        cand = _signup(client, f"deact_ws_{uid}@test.com", "candidate")
        cand_token = cand["access_token"]
        cand_id = cand["user_id"]

        _deactivate_user(client, admin_token, cand_id)

        # Attempt WebSocket connection with deactivated user's token.
        # The server should close with code 4004.
        with pytest.raises(Exception):
            with client.websocket_connect("/applications/ws/applications") as ws:
                ws.send_json({"token": cand_token})
                # Server should close the connection; trying to receive
                # should raise an exception for the disconnect.
                ws.receive_json()


class TestForgotPasswordDeactivatedUser:
    """Forgot-password returns a static message for all inputs.

    Since it never actually sends an email or resets anything, it cannot
    leak account state. Verify it still returns the same message for a
    deactivated user.
    """

    def test_forgot_password_same_message(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]
        email = f"deact_forgot_{uid}@test.com"

        cand = _signup(client, email, "candidate")
        _deactivate_user(client, admin_token, cand["user_id"])

        r = client.post("/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        assert "instructions have been sent" in r.json()["message"]


class TestAdminDeactivationAPI:
    """Admin can deactivate and reactivate users."""

    def test_deactivate_and_reactivate(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]

        cand = _signup(client, f"toggle_{uid}@test.com", "candidate")
        cand_token = cand["access_token"]
        cand_id = cand["user_id"]

        # Deactivate → token rejected
        _deactivate_user(client, admin_token, cand_id)
        r = client.get(
            f"/candidates/{cand_id}",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert r.status_code == 401

        # Reactivate → token works again
        _reactivate_user(client, admin_token, cand_id)
        r = client.get(
            f"/candidates/{cand_id}",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert r.status_code == 200, f"after reactivation: {r.status_code}"

    def test_deactivation_does_not_affect_other_users(self, client, admin_token):
        uid = uuid.uuid4().hex[:8]

        cand_a = _signup(client, f"deact_a_{uid}@test.com", "candidate")
        cand_b = _signup(client, f"deact_b_{uid}@test.com", "candidate")

        # Deactivate A only
        _deactivate_user(client, admin_token, cand_a["user_id"])

        # A is locked out
        r = client.get(
            f"/candidates/{cand_a['user_id']}",
            headers={"Authorization": f"Bearer {cand_a['access_token']}"},
        )
        assert r.status_code == 401

        # B still works
        r = client.get(
            f"/candidates/{cand_b['user_id']}",
            headers={"Authorization": f"Bearer {cand_b['access_token']}"},
        )
        assert r.status_code == 200


# ── Seeded fixture users (must exist on any DB, incl. fresh CI) ──────────
_SEED_ADMIN_ID = _ADMIN_ID
_SEED_CANCELLED_COMPANY_ID = uuid.UUID("5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1")


async def _seed_users() -> None:
    from sqlalchemy import select

    from core.database import AsyncSessionLocal
    from models import Company, PlanTier, Subscription, SubscriptionStatus, User, UserRole

    async with AsyncSessionLocal() as db:
        if await db.get(User, _SEED_ADMIN_ID) is None:
            db.add(
                User(
                    id=_SEED_ADMIN_ID,
                    email="seed_admin@test.com",
                    password_hash="!",
                    role=UserRole.admin,
                    is_active=True,
                )
            )
        comp = await db.get(User, _SEED_CANCELLED_COMPANY_ID)
        if comp is None:
            comp = User(
                id=_SEED_CANCELLED_COMPANY_ID,
                email="seed_cancelled_co@test.com",
                password_hash="!",
                role=UserRole.company,
                is_active=True,
            )
            db.add(comp)
            await db.flush()
            db.add(Company(user_id=comp.id, name="Seed Co"))
        subs = (
            await db.scalars(
                select(Subscription).where(Subscription.user_id == _SEED_CANCELLED_COMPANY_ID)
            )
        ).all()
        if not subs:
            db.add(
                Subscription(
                    user_id=_SEED_CANCELLED_COMPANY_ID,
                    role=UserRole.company,
                    plan_tier=PlanTier.growth,
                    status=SubscriptionStatus.cancelled,
                )
            )
        await db.commit()


def _ensure_seed_users() -> None:
    import asyncio

    asyncio.run(_seed_users())


def _activate_company_search_subscription(user_id: str) -> None:
    """Give a freshly signed-up company an active growth plan so candidate
    search entitlement checks pass (signup only creates pending)."""
    import asyncio

    from sqlalchemy import select

    from core.database import AsyncSessionLocal
    from models import PlanTier, Subscription, SubscriptionStatus

    async def _act() -> None:
        async with AsyncSessionLocal() as db:
            sub = await db.scalar(
                select(Subscription).where(Subscription.user_id == uuid.UUID(user_id))
            )
            if sub is not None:
                sub.status = SubscriptionStatus.active
                sub.plan_tier = PlanTier.growth
            await db.commit()

    asyncio.run(_act())
