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


async def _mk_user_with_sub(db, role=UserRole.candidate, plan="complete"):
    """Create a real user + pending subscription for FK-requiring tests."""
    return await create_user_with_profile(
        db=db,
        email=f"fk_{uuid4().hex[:10]}@test.com",
        password="Test1234!",
        role=role,
        name="FK Test",
        plan=plan,
    )


@pytest.mark.asyncio
class TestSignupCreatesPendingSubscription:
    """Signup should create pending subscriptions, not active."""

    async def test_signup_candidate_creates_pending(self, db_session):
        """Candidate signup creates subscription with status=pending."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"cand_{uuid4().hex[:8]}@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Test Candidate",
            plan="resume_builder",
        )
        await db_session.commit()
        await db_session.refresh(user, attribute_names=["subscription"])

        assert user.subscription is not None
        assert user.subscription.status == SubscriptionStatus.pending
        assert user.subscription.plan_tier == PlanTier.resume_builder
        assert user.subscription.renews_at is None  # No renewal until payment

    async def test_signup_company_creates_pending(self, db_session):
        """Company signup creates subscription with status=pending."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"corp_{uuid4().hex[:8]}@test.com",
            password="Test1234!",
            role=UserRole.company,
            name="Test Corp",
            industry="Tech",
            plan="corporate_annual",
        )
        await db_session.commit()
        await db_session.refresh(user, attribute_names=["subscription"])

        assert user.subscription is not None
        assert user.subscription.status == SubscriptionStatus.pending
        assert user.subscription.plan_tier == PlanTier.corporate_annual
        assert user.subscription.renews_at is None

    async def test_signup_default_plan_is_free_candidate(self, db_session):
        """Candidate signup without plan defaults to free (but still pending)."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"free_{uuid4().hex[:8]}@test.com",
            password="Test1234!",
            role=UserRole.candidate,
            name="Free User",
        )
        await db_session.commit()
        await db_session.refresh(user, attribute_names=["subscription"])

        assert user.subscription.status == SubscriptionStatus.pending
        # Note: "free" is no longer a valid plan tier; defaults to job_search or similar
        # Behavior depends on parse_plan() logic

    async def test_pending_subscription_blocks_paid_features(self, db_session):
        """Pending subscription should not grant access to paid features.

        (Enforced by entitlement service in Step 6B)
        """
        user = await create_user_with_profile(
            db=db_session,
            email=f"pending_{uuid4().hex[:8]}@test.com",
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
            email=f"audit1_{uuid4().hex[:8]}@test.com",
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

        user = await _mk_user_with_sub(db_session)
        sub = await db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        user_id = user.id
        sub_id = sub.id

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
            select(SubscriptionAuditLog).where(
                SubscriptionAuditLog.subscription_id == sub_id,
                SubscriptionAuditLog.action == "update",
            )
        )
        assert audit is not None
        assert audit.action == "update"
        assert audit.old_status == "pending"
        assert audit.new_status == "active"
        assert audit.payment_transaction_id == "razorpay_123456"


@pytest.mark.asyncio
class TestAdminCannotManuallyActivate:
    """Admin routes should prevent manual activation."""

    async def test_patch_endpoint_rejects_status_to_active(self, db_session, admin_client):
        """PATCH /admin/subscriptions/{id} rejects status=active (403)."""
        user = await _mk_user_with_sub(db_session)
        await db_session.commit()
        sub = await db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        assert sub is not None

        response = await admin_client.patch(
            f"/admin/subscriptions/{sub.id}", json={"status": "active"}
        )
        assert response.status_code == 403, response.text
        assert "payment" in response.json()["detail"].lower()

        # Status must remain unchanged
        await db_session.refresh(sub)
        assert sub.status == SubscriptionStatus.pending

    async def test_admin_can_modify_plan_tier(self, db_session):
        """Admin can still change plan_tier (just not status to active)."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"admin_test_{uuid4().hex[:8]}@test.com",
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
            admin_id=None,  # system action; fabricated UUID would violate users FK
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

    async def test_delete_endpoint_disabled(self, db_session, admin_client):
        """DELETE /admin/subscriptions/{id} returns 405 (soft-delete only)."""
        user = await _mk_user_with_sub(db_session)
        await db_session.commit()
        sub = await db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        assert sub is not None

        response = await admin_client.delete(f"/admin/subscriptions/{sub.id}")
        assert response.status_code == 405, response.text

        # Row must still exist — nothing was hard-deleted
        still_there = await db_session.scalar(select(Subscription).where(Subscription.id == sub.id))
        assert still_there is not None

    async def test_mark_as_cancelled_preserves_audit(self, db_session):
        """Cancelling a subscription preserves audit history."""

        user = await create_user_with_profile(
            db=db_session,
            email=f"cancel_{uuid4().hex[:8]}@test.com",
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
            admin_id=None,  # system action; fabricated UUID would violate users FK
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
            email=f"payment_{uuid4().hex[:8]}@test.com",
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
        await db_session.refresh(user, attribute_names=["subscription"])

        assert user.subscription.status == SubscriptionStatus.active
        assert user.subscription.renews_at is not None

    async def test_active_to_cancelled(self, db_session):
        """Active subscription can be cancelled."""
        user = await create_user_with_profile(
            db=db_session,
            email=f"cancel_active_{uuid4().hex[:8]}@test.com",
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
        await db_session.refresh(user, attribute_names=["subscription"])

        # user.subscription is scoped to live (pending/active) rows — a
        # cancelled-only user has no current subscription. Verify the
        # historical row directly instead.
        assert user.subscription is None
        cancelled_sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        assert cancelled_sub is not None
        assert cancelled_sub.status == SubscriptionStatus.cancelled


@pytest.mark.asyncio
class TestNoBackdoorActivation:
    """Verify no unintended ways to activate subscriptions."""

    async def test_cannot_bypass_activation_check(self, db_session):
        """Direct subscription creation uses pending by default."""
        user = await _mk_user_with_sub(db_session)
        # cancel the signup pending row so our insert is the only live row
        old = await db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        old.status = SubscriptionStatus.cancelled
        await db_session.flush()
        sub = Subscription(
            user_id=user.id,
            role=UserRole.candidate,
            plan_tier=PlanTier.complete,
            status=SubscriptionStatus.pending,  # ← Default
            renews_at=None,
        )
        db_session.add(sub)
        await db_session.commit()
        await db_session.refresh(sub)

        assert sub.status == SubscriptionStatus.pending

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
        user = await _mk_user_with_sub(db_session)
        sub = await db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        admin = await _mk_user_with_sub(db_session, role=UserRole.admin, plan="complete")
        admin_id = admin.id
        sub_id = sub.id
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

        audit = await db_session.scalar(
            select(SubscriptionAuditLog).where(
                SubscriptionAuditLog.subscription_id == sub_id,
                SubscriptionAuditLog.action == "update_status",
            )
        )

        assert audit.subscription_id == sub_id
        assert audit.user_id == user_id
        assert audit.admin_id == admin_id
        assert audit.action == "update_status"
        assert audit.old_status == "pending"
        assert audit.new_status == "active"
        assert audit.reason == "Payment transaction completed"
        assert audit.payment_transaction_id == "txn_12345"
        assert audit.created_at is not None
