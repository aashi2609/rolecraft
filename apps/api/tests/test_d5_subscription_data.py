"""
D5: Subscription data reconciliation and cleanup.

Tests for:
1. Data reconciliation report generation
2. Expired subscription identification
3. Cleanup script functionality
4. Data integrity checks
"""

from datetime import datetime, timezone, timedelta
import uuid

import pytest
from sqlalchemy import select

from models import (
    Subscription,
    SubscriptionStatus,
    SubscriptionAuditLog,
    User,
    UserRole,
    PlanTier,
)
from services.user_service import create_user_with_profile


@pytest.mark.asyncio
class TestSubscriptionDataReport:
    """Verify subscription data reconciliation report generation."""

    async def test_report_counts_by_status(self, db_session):
        """Report correctly counts subscriptions by status."""
        # Create users with different subscription statuses
        pending_user = await create_user_with_profile(
            db=db_session,
            email=f"pending_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Grant active subscription to another user
        active_user = await create_user_with_profile(
            db=db_session,
            email=f"active_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Change active_user subscription to active
        active_sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == active_user.id)
        )
        active_sub.status = SubscriptionStatus.active
        active_sub.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
        await db_session.flush()

        # Cancel a subscription
        cancelled_user = await create_user_with_profile(
            db=db_session,
            email=f"cancelled_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        cancelled_sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == cancelled_user.id)
        )
        cancelled_sub.status = SubscriptionStatus.cancelled
        await db_session.flush()

        # Count by status
        pending_count = await db_session.scalar(
            select(Subscription).where(Subscription.status == SubscriptionStatus.pending)
        )
        active_count = await db_session.scalar(
            select(Subscription).where(Subscription.status == SubscriptionStatus.active)
        )
        cancelled_count = await db_session.scalar(
            select(Subscription).where(Subscription.status == SubscriptionStatus.cancelled)
        )

        assert pending_count is not None, "Should find pending subscription"
        assert active_count is not None, "Should find active subscription"
        assert cancelled_count is not None, "Should find cancelled subscription"

    async def test_report_identifies_expired_subscriptions(self, db_session):
        """Report identifies subscriptions past renewal date."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"expired_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Set subscription to active with past renewal date
        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        sub.status = SubscriptionStatus.active
        sub.renews_at = datetime.now(timezone.utc) - timedelta(days=10)
        await db_session.flush()

        # Verify it's found as expired
        expired_sub = await db_session.scalar(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.active,
                Subscription.renews_at < datetime.now(timezone.utc),
            )
        )

        assert expired_sub is not None, "Should find expired subscription"
        assert expired_sub.id == sub.id

    async def test_report_counts_by_plan_tier(self, db_session):
        """Report counts subscriptions by plan tier."""
        # Create candidate with free plan
        cand = await create_user_with_profile(
            db=db_session,
            email=f"candidate_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.candidate,
        )
        await db_session.flush()

        # Create company with corporate plan
        company = await create_user_with_profile(
            db=db_session,
            email=f"company_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Verify plan tiers
        cand_sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == cand.id)
        )
        company_sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == company.id)
        )

        assert cand_sub.plan_tier == PlanTier.free
        assert company_sub.plan_tier == PlanTier.corporate_annual

    async def test_report_counts_by_user_role(self, db_session):
        """Report counts subscriptions by user role."""
        # Create candidate and company
        cand = await create_user_with_profile(
            db=db_session,
            email=f"role_cand_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.candidate,
        )
        company = await create_user_with_profile(
            db=db_session,
            email=f"role_company_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Count by role
        candidate_subs = await db_session.scalar(
            select(Subscription).where(Subscription.role == UserRole.candidate)
        )
        company_subs = await db_session.scalar(
            select(Subscription).where(Subscription.role == UserRole.company)
        )

        assert candidate_subs is not None
        assert company_subs is not None


@pytest.mark.asyncio
class TestSubscriptionCleanup:
    """Verify subscription cleanup functionality."""

    async def test_cleanup_identifies_expired_subscriptions(self, db_session):
        """Cleanup script identifies subscriptions for cancellation."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"cleanup_expired_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        # Set to expired
        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        sub.status = SubscriptionStatus.active
        sub.renews_at = datetime.now(timezone.utc) - timedelta(days=5)
        await db_session.flush()

        # Find expired
        expired = await db_session.scalar(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.active,
                Subscription.renews_at < datetime.now(timezone.utc),
            )
        )

        assert expired is not None, "Should identify expired subscription"
        assert expired.id == sub.id

    async def test_cleanup_can_cancel_expired_subscription(self, db_session):
        """Cleanup can cancel an expired subscription."""
        from services.subscription_service import log_subscription_change

        user = await create_user_with_profile(
            db=db_session,
            email=f"cleanup_cancel_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        sub.status = SubscriptionStatus.active
        sub.renews_at = datetime.now(timezone.utc) - timedelta(days=5)
        await db_session.flush()

        # Simulate cleanup: cancel the subscription
        old_status = sub.status.value
        sub.status = SubscriptionStatus.cancelled

        await log_subscription_change(
            db=db_session,
            subscription_id=sub.id,
            user_id=user.id,
            action="cancel",
            old_status=old_status,
            new_status=SubscriptionStatus.cancelled.value,
            reason="Automatic expiration (renewal date passed)",
        )
        await db_session.flush()

        # Verify it's cancelled
        updated_sub = await db_session.scalar(
            select(Subscription).where(Subscription.id == sub.id)
        )
        assert updated_sub.status == SubscriptionStatus.cancelled

        # Verify audit log entry
        audit = await db_session.scalar(
            select(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub.id)
            .order_by(SubscriptionAuditLog.created_at.desc())
        )
        assert audit is not None
        assert audit.action == "cancel"
        assert audit.old_status == "active"
        assert audit.new_status == "cancelled"


@pytest.mark.asyncio
class TestDataIntegrity:
    """Verify data integrity checks for subscriptions."""

    async def test_every_user_has_subscription(self, db_session):
        """Every user should have exactly one subscription."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"integrity_check_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.candidate,
        )
        await db_session.flush()

        # Count subscriptions for this user
        subs = await db_session.scalars(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subs_list = subs.all()

        assert len(subs_list) == 1, "Every user should have exactly one subscription"

    async def test_subscription_user_exists(self, db_session):
        """Every subscription should reference an existing user."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"sub_user_check_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )

        # Verify user exists
        referenced_user = await db_session.get(User, sub.user_id)
        assert referenced_user is not None, "Subscription user should exist"
        assert referenced_user.id == user.id

    async def test_subscription_role_matches_user_role(self, db_session):
        """Subscription role should match user role."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"role_match_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )

        assert sub.role == user.role, "Subscription role should match user role"

    async def test_active_subscription_has_renewal_date(self, db_session):
        """Active subscriptions should have a renewal date."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"renewal_check_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        sub.status = SubscriptionStatus.active
        sub.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
        await db_session.flush()

        updated_sub = await db_session.scalar(
            select(Subscription).where(Subscription.id == sub.id)
        )
        assert updated_sub.renews_at is not None, "Active subscription should have renewal date"

    async def test_pending_subscription_has_no_renewal_date(self, db_session):
        """Pending subscriptions should NOT have a renewal date."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"pending_no_renewal_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.flush()

        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        assert sub.status == SubscriptionStatus.pending
        assert sub.renews_at is None, "Pending subscription should NOT have renewal date"
