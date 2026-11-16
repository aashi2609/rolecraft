"""Subscription invariant tests (Part 2).

Covers: get_current_subscription state matrix, one-live-row invariant
(partial unique index), admin create 409, signup pending row, and the
GET /subscriptions/me 200 contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.dependencies import get_user_plan
from models import PlanTier, Subscription, SubscriptionStatus, UserRole
from services.entitlement_service import get_entitlements
from services.subscription_service import get_current_subscription
from services.user_service import create_user_with_profile

pytestmark = pytest.mark.asyncio


async def _sub(db, user, status, plan=PlanTier.free, renews_at=None, started_at=None):
    s = Subscription(
        user_id=user.id,
        role=user.role,
        plan_tier=plan,
        status=status,
        started_at=started_at or datetime.now(timezone.utc),
        renews_at=renews_at,
    )
    db.add(s)
    await db.commit()
    return s


async def _candidate(db):
    return await create_user_with_profile(
        db=db, email=f"inv_cand_{uuid.uuid4().hex[:8]}@test.com",
        password="TestPass123", role=UserRole.candidate,
    )


class TestGetCurrentSubscriptionMatrix:
    """State matrix against the single reader."""

    async def test_none_returns_none(self, db_session):
        u = await _candidate(db_session)
        # remove signup pending row to simulate no subscription
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            await db_session.delete(s)
        await db_session.commit()
        assert await get_current_subscription(db_session, u.id) is None

    async def test_pending_returned_but_no_plan(self, db_session):
        u = await _candidate(db_session)  # signup creates pending
        sub = await get_current_subscription(db_session, u.id)
        assert sub is not None and sub.status == SubscriptionStatus.pending
        assert await get_user_plan(u, db_session) is None
        ent = await get_entitlements(u, db_session)
        assert ent.is_active is False

    async def test_active_returns_plan(self, db_session):
        u = await _candidate(db_session)
        # clear signup pending so active is the only live row
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            await db_session.delete(s)
        await db_session.commit()
        await _sub(db_session, u, SubscriptionStatus.active,
                   plan=PlanTier.job_search,
                   renews_at=datetime.now(timezone.utc) + timedelta(days=30))
        sub = await get_current_subscription(db_session, u.id)
        assert sub is not None and sub.status == SubscriptionStatus.active
        assert await get_user_plan(u, db_session) == PlanTier.job_search
        ent = await get_entitlements(u, db_session)
        assert ent.is_active is True

    async def test_expired_active_gives_no_entitlement(self, db_session):
        u = await _candidate(db_session)
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            await db_session.delete(s)
        await db_session.commit()
        await _sub(db_session, u, SubscriptionStatus.active,
                   plan=PlanTier.job_search,
                   renews_at=datetime.now(timezone.utc) - timedelta(days=1))
        assert await get_current_subscription(db_session, u.id) is None
        ent = await get_entitlements(u, db_session)
        assert ent.is_active is False

    async def test_cancelled_only_returns_none(self, db_session):
        u = await _candidate(db_session)
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            await db_session.delete(s)
        await db_session.commit()
        await _sub(db_session, u, SubscriptionStatus.cancelled)
        assert await get_current_subscription(db_session, u.id) is None

    async def test_cancelled_plus_active_returns_active(self, db_session):
        u = await _candidate(db_session)
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            await db_session.delete(s)
        await db_session.commit()
        await _sub(db_session, u, SubscriptionStatus.cancelled,
                   started_at=datetime.now(timezone.utc) - timedelta(days=400))
        new = await _sub(db_session, u, SubscriptionStatus.active,
                         plan=PlanTier.job_search,
                         renews_at=datetime.now(timezone.utc) + timedelta(days=30))
        sub = await get_current_subscription(db_session, u.id)
        assert sub is not None and sub.id == new.id


class TestOneLiveRowInvariant:
    async def test_second_live_row_raises_integrity_error(self, db_session):
        u = await _candidate(db_session)
        # signup pending exists -> inserting another pending must violate index
        with pytest.raises(IntegrityError):
            db_session.add(Subscription(
                user_id=u.id, role=u.role,
                plan_tier=PlanTier.job_search,
                status=SubscriptionStatus.pending,
            ))
            await db_session.flush()
        await db_session.rollback()

    async def test_cancelled_rows_do_not_count(self, db_session):
        u = await _candidate(db_session)
        for s in (await db_session.scalars(select(Subscription).where(Subscription.user_id == u.id))).all():
            s.status = SubscriptionStatus.cancelled
        await db_session.commit()
        s2 = await _sub(db_session, u, SubscriptionStatus.pending,
                        plan=PlanTier.job_search)
        assert s2.status == SubscriptionStatus.pending

    async def test_admin_create_second_live_returns_409(self, admin_client, db_session):
        u = await _candidate(db_session)
        await db_session.commit()  # visible to the app session
        resp = await admin_client.post("/admin/subscriptions", json={
            "user_id": str(u.id), "role": "candidate",
            "plan_tier": "job_search", "status": "pending",
        })
        assert resp.status_code == 409
        assert "live subscription" in resp.json()["detail"].lower()


class TestSubscriptionsMeContract:
    async def test_no_subscription_returns_200_plan_null(
        self, candidate_client, candidate_user
    ):
        # candidate_user fixture has no subscription row at all
        resp = await candidate_client.get("/subscriptions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] is None
        assert data["status"] == "none"
        assert "entitlements" in data

    async def test_pending_subscription_returns_200(
        self, db_session, candidate_client, candidate_user
    ):
        await _sub(db_session, candidate_user, SubscriptionStatus.pending,
                   plan=PlanTier.job_search)
        resp = await candidate_client.get("/subscriptions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["plan"] is not None

    async def test_signup_creates_exactly_one_pending_row(
        self, db_session
    ):
        for role, plan in ((UserRole.candidate, None), (UserRole.company, None)):
            u = await create_user_with_profile(
                db=db_session,
                email=f"signup_{role.value}_{uuid.uuid4().hex[:8]}@test.com",
                password="TestPass123", role=role,
            )
            await db_session.commit()
            subs = (
                await db_session.scalars(
                    select(Subscription).where(Subscription.user_id == u.id)
                )
            ).all()
            assert len(subs) == 1
            assert subs[0].status == SubscriptionStatus.pending
            assert subs[0].role == role

    async def test_lifetime_active_has_no_expiry(
        self, db_session, candidate_client, candidate_user
    ):
        # clear pending, add lifetime active (renews_at NULL)
        for s in (
            await db_session.scalars(
                select(Subscription).where(Subscription.user_id == candidate_user.id)
            )
        ).all():
            await db_session.delete(s)
        await db_session.commit()
        await _sub(db_session, candidate_user, SubscriptionStatus.active,
                   plan=PlanTier.complete, renews_at=None)
        sub = await get_current_subscription(db_session, candidate_user.id)
        assert sub is not None and sub.renews_at is None
        resp = await candidate_client.get("/subscriptions/me")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"
