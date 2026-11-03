"""Step 6A: Subscription audit logging and payment verification fixes.

Verify:
1. Signup creates pending (not active) subscriptions
2. Admin cannot manually activate subscriptions
3. All subscription changes logged to audit table
4. Hard delete disabled, soft delete only
5. Admin can still modify plan_tier and role
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from models import (
    PlanTier,
    Subscription,
    SubscriptionAuditLog,
    SubscriptionStatus,
    UserRole,
)
from routers.admin import SubCreate
from services.subscription_service import log_subscription_change
from services.user_service import create_user_with_profile


@pytest.mark.asyncio
class TestSignupCreatesPendingSubscription:
    """Signup should create pending subscriptions, not active."""

    async def test_signup_candidate_creates_pending(self, db_session):
        """Candidate signup creates subscription with status=pending."""
        user = await create_user_with_profile(
            db=db_session,
            email="cand@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Test Candidate",
            plan="resume_builder",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])

        assert user.subscription is not None
        assert user.subscription.status == SubscriptionStatus.pending
        assert user.subscription.plan_tier == PlanTier.resume_builder
        assert user.subscription.renews_at is None  # No renewal until payment

    async def test_signup_company_creates_pending(self, db_session):
        """Company signup creates subscription with status=pending."""
        user = await create_user_with_profile(
            db=db_session,
            email="corp@test.com",
            password="Test1234!",
            role=UserRole.company,
            name="Test Corp",
            industry="Tech",
            plan="corporate_annual",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])

        assert user.subscription is not None
        assert user.subscription.status == SubscriptionStatus.pending
        assert user.subscription.plan_tier == PlanTier.corporate_annual
        assert user.subscription.renews_at is None

    async def test_signup_default_plan_is_free_candidate(self, db_session):
        """Candidate signup without plan defaults to free (but still pending)."""
        user = await create_user_with_profile(
            db=db_session,
            email="free@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Free User",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])

        assert user.subscription.status == SubscriptionStatus.pending
        # Note: "free" is no longer a valid plan tier; defaults to job_search or similar
        # Behavior depends on parse_plan() logic

    async def test_pending_subscription_blocks_paid_features(self, db_session):
        """Pending subscription should not grant access to paid features.

        (Enforced by entitlement service in Step 6B)
        """
        user = await create_user_with_profile(
            db=db_session,
            email="pending@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            plan="complete",
        )
        await db_session.commit()

        # Subscription is pending, not active
        assert user.subscription.status == SubscriptionStatus.pending


@pytest.mark.asyncio
class TestAuditLogging:
    """All subscription changes must be logged."""

    async def test_signup_creates_audit_log_entry(self, db_session):
        """Signup should create an audit log entry."""

        user = await create_user_with_profile(
            db=db_session,
            email="audit1@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            plan="job_search",
        )
        await db_session.commit()

        # Check audit log
        audit = await db_session.scalar(
            select(SubscriptionAuditLog).where(
                SubscriptionAuditLog.subscription_id == user.subscription.id
            )
        )
        assert audit is not None
        assert audit.action == "create"
        assert audit.new_status == "pending"
        assert audit.reason == "User registration"
        assert audit.admin_id is None  # System action

    async def test_manual_audit_log_entry(self, db_session):
        """Manual subscription change can be logged."""
        # Create actual user and subscription first
        user = await create_user_with_profile(
            db=db_session,
            email="manual@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Manual Test",
            plan="resume_builder",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])
        
        sub_id = user.subscription.id
        user_id = user.id

        await log_subscription_change(
            db=db_session,
            subscription_id=sub_id,
            user_id=user_id,
            action="update",
            admin_id=None,
            old_status="pending",
            new_status="active",
            reason="Payment verified - Razorpay transaction 123456",
            payment_transaction_id="razorpay_123456",
        )
        await db_session.commit()

        audit = await db_session.scalar(
            select(SubscriptionAuditLog).where(SubscriptionAuditLog.subscription_id == sub_id)
        )
        # Should have 2 entries: create (from signup) + update (manual)
        assert audit is not None
        # Get the update entry specifically
        audits = (await db_session.execute(
            select(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub_id)
            .where(SubscriptionAuditLog.action == "update")
        )).scalars().all()
        
        assert len(audits) > 0
        update_audit = audits[0]
        assert update_audit.action == "update"
        assert update_audit.old_status == "pending"
        assert update_audit.new_status == "active"
        assert update_audit.payment_transaction_id == "razorpay_123456"


@pytest.mark.asyncio
class TestAdminCannotManuallyActivate:
    """Admin routes should prevent manual activation."""

    async def test_patch_endpoint_rejects_status_to_active(
        self, db_session, candidate_user, current_admin
    ):
        """PATCH /admin/subscriptions/{id} rejects status=active."""
        # This test requires a proper admin user and route setup
        # Placeholder for integration test - skip for now
        pytest.skip("Integration test placeholder - requires full route setup")

    async def test_admin_can_modify_plan_tier(self, db_session):
        """Admin can still change plan_tier (just not status to active)."""
        user = await create_user_with_profile(
            db=db_session,
            email="admin_test@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            plan="job_search",
        )
        await db_session.commit()

        # Admin upgrades plan (but status stays pending)
        old_status = user.subscription.status.value
        old_plan = user.subscription.plan_tier.value

        user.subscription.plan_tier = PlanTier.complete

        await log_subscription_change(
            db=db_session,
            subscription_id=user.subscription.id,
            user_id=user.id,
            admin_id=uuid4(),
            action="update",
            old_plan_tier=old_plan,
            new_plan_tier=PlanTier.complete.value,
            old_status=old_status,
            new_status=old_status,
            reason="Admin plan upgrade",
        )
        await db_session.commit()

        assert user.subscription.plan_tier == PlanTier.complete
        assert user.subscription.status == SubscriptionStatus.pending  # Still pending!


@pytest.mark.asyncio
class TestSoftDelete:
    """Hard delete disabled; must use soft delete (mark as cancelled)."""

    async def test_delete_endpoint_disabled(self, db_session, candidate_user):
        """DELETE /admin/subscriptions/{id} returns 405."""
        # Integration test would call the route and assert 405
        # Placeholder for route testing - skip for now
        pytest.skip("Integration test placeholder - requires full route setup")

    async def test_mark_as_cancelled_preserves_audit(self, db_session):
        """Cancelling a subscription preserves audit history."""

        user = await create_user_with_profile(
            db=db_session,
            email="cancel@test.com",
            password="Test1234!",
            role=UserRole.candidate,
        )
        await db_session.commit()

        sub_id = user.subscription.id
        user_id = user.id

        # Record initial creation
        initial_audit_count = await db_session.scalar(
            select(func.count())
            .select_from(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub_id)
        )

        # Soft-delete (mark as cancelled)
        user.subscription.status = SubscriptionStatus.cancelled
        await log_subscription_change(
            db=db_session,
            subscription_id=sub_id,
            user_id=user_id,
            admin_id=uuid4(),
            action="cancel",
            old_status="pending",
            new_status="cancelled",
            reason="User request",
        )
        await db_session.commit()

        # Verify audit trail preserved
        final_audit_count = await db_session.scalar(
            select(func.count())
            .select_from(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub_id)
        )
        assert final_audit_count > initial_audit_count


@pytest.mark.asyncio
class TestSubscriptionTransitions:
    """Test valid subscription status transitions."""

    async def test_pending_to_active_via_payment(self, db_session):
        """Subscription transitions pending -> active via payment verification."""
        user = await create_user_with_profile(
            db=db_session,
            email="payment@test.com",
            password="Test1234!",
            role=UserRole.candidate,
        )
        await db_session.commit()

        assert user.subscription.status == SubscriptionStatus.pending

        # Simulate payment verification (would come from webhook)
        from datetime import timedelta, timezone

        user.subscription.status = SubscriptionStatus.active
        user.subscription.renews_at = datetime.now(timezone.utc) + timedelta(days=30)

        await log_subscription_change(
            db=db_session,
            subscription_id=user.subscription.id,
            user_id=user.id,
            action="update",
            old_status="pending",
            new_status="active",
            reason="Payment verified",
            payment_transaction_id="razorpay_payment_id",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])

        assert user.subscription.status == SubscriptionStatus.active
        assert user.subscription.renews_at is not None

    async def test_active_to_cancelled(self, db_session):
        """Active subscription can be cancelled."""
        user = await create_user_with_profile(
            db=db_session,
            email="cancel_active@test.com",
            password="Test1234!",
            role=UserRole.candidate,
        )
        # Manually set to active for test
        user.subscription.status = SubscriptionStatus.active
        await db_session.commit()

        user.subscription.status = SubscriptionStatus.cancelled
        await log_subscription_change(
            db=db_session,
            subscription_id=user.subscription.id,
            user_id=user.id,
            action="cancel",
            old_status="active",
            new_status="cancelled",
            reason="User cancellation request",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])

        assert user.subscription.status == SubscriptionStatus.cancelled


@pytest.mark.asyncio
class TestNoBackdoorActivation:
    """Verify no unintended ways to activate subscriptions."""

    async def test_cannot_bypass_activation_check(self, db_session):
        """Direct subscription creation uses pending by default."""
        # Create user first
        user = await create_user_with_profile(
            db=db_session,
            email="bypass@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Bypass Test",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])
        
        # Verify the created subscription defaults to pending
        assert user.subscription.status == SubscriptionStatus.pending

    async def test_subcreateschema_defaults_to_pending(self, db_session):
        """SubCreate schema defaults to pending."""
        data = SubCreate(
            user_id=str(uuid4()),
            role="candidate",
            plan_tier="complete",
            # status not provided; should default to pending
        )
        assert data.status == SubscriptionStatus.pending


@pytest.mark.asyncio
class TestAuditLogIntegrity:
    """Audit log captures all required information."""

    async def test_audit_entry_has_all_fields(self, db_session):
        """Audit log entry includes all trackable fields."""
        # Create real user and admin
        admin_user = await create_user_with_profile(
            db=db_session,
            email="admin_audit@test.com",
            password="Test1234!",
            role=UserRole.admin,
            name="Admin Audit",
        )
        
        user = await create_user_with_profile(
            db=db_session,
            email="user_audit@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="User Audit",
            plan="complete",
        )
        await db_session.commit()
        await db_session.refresh(user, ["subscription"])
        
        admin_id = admin_user.id
        sub_id = user.subscription.id
        user_id = user.id

        await log_subscription_change(
            db=db_session,
            subscription_id=sub_id,
            user_id=user_id,
            admin_id=admin_id,
            action="update_status",
            old_status="pending",
            new_status="active",
            reason="Payment transaction completed",
            payment_transaction_id="txn_12345",
        )
        await db_session.commit()

        # Get the update_status audit entry (not the initial create one)
        audits = (await db_session.execute(
            select(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub_id)
            .where(SubscriptionAuditLog.action == "update_status")
        )).scalars().all()
        
        assert len(audits) > 0
        audit = audits[0]

        assert audit.subscription_id == sub_id
        assert audit.user_id == user_id
        assert audit.admin_id == admin_id
        assert audit.action == "update_status"
        assert audit.old_status == "pending"
        assert audit.new_status == "active"
        assert audit.reason == "Payment transaction completed"
        assert audit.payment_transaction_id == "txn_12345"
        assert audit.created_at is not None
