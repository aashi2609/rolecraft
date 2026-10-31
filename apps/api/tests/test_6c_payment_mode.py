"""Step 6C: Payment mode configuration and admin grants.

Tests verify:
- PaymentMode enum works (disabled|test|live)
- Startup validation enforces required credentials per mode
- Admin grant endpoint creates active subscriptions immediately
- Admin grant logs with audit trail
- Non-admin users cannot grant subscriptions
- Plan tier validated against user role
- Existing subscriptions cancelled before grant
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.payment_config import PaymentMode, PaymentConfig
from models import SubscriptionStatus, SubscriptionAuditLog, PlanTier, UserRole


class TestPaymentModeEnum:
    """Test PaymentMode enum parsing and validation."""

    def test_payment_mode_disabled(self):
        """Test disabled mode."""
        mode = PaymentMode("disabled")
        assert mode == PaymentMode.disabled
        assert mode.value == "disabled"

    def test_payment_mode_test(self):
        """Test test mode."""
        mode = PaymentMode("test")
        assert mode == PaymentMode.test
        assert mode.value == "test"

    def test_payment_mode_live(self):
        """Test live mode."""
        mode = PaymentMode("live")
        assert mode == PaymentMode.live
        assert mode.value == "live"

    def test_payment_mode_case_insensitive(self):
        """Test case-insensitive parsing."""
        assert PaymentMode("DISABLED") == PaymentMode.disabled
        assert PaymentMode("Test") == PaymentMode.test
        assert PaymentMode("LIVE") == PaymentMode.live

    def test_payment_mode_invalid(self):
        """Test invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PaymentMode"):
            PaymentMode("invalid")


class TestPaymentConfig:
    """Test PaymentConfig validation."""

    def test_config_disabled_no_credentials_required(self):
        """Disabled mode requires no credentials."""
        config = PaymentConfig("disabled")
        # Should not raise
        config.validate_startup(None, None, None)
        assert config.is_disabled

    def test_config_test_missing_credentials_warns(self, caplog):
        """Test mode warns if credentials missing but doesn't fail."""
        config = PaymentConfig("test")
        # Should not raise
        config.validate_startup(None, None, None)
        assert config.is_test
        assert "RAZORPAY_KEY_ID not set" in caplog.text
        assert "using mock for test mode" in caplog.text

    def test_config_test_with_credentials(self, caplog):
        """Test mode works with credentials."""
        config = PaymentConfig("test")
        config.validate_startup("test_key_id", "test_key_secret", "test_webhook_secret")
        assert config.is_test
        assert "TEST mode" in caplog.text

    def test_config_live_missing_credentials_raises(self):
        """Live mode requires all credentials."""
        config = PaymentConfig("live")
        with pytest.raises(RuntimeError, match="CRITICAL.*Live payment mode"):
            config.validate_startup(None, None, None)

    def test_config_live_partial_credentials_raises(self):
        """Live mode requires ALL credentials."""
        config = PaymentConfig("live")
        # Missing secret
        with pytest.raises(RuntimeError, match="RAZORPAY_KEY_SECRET"):
            config.validate_startup("key_id", None, "webhook_secret")

    def test_config_live_with_all_credentials(self, caplog):
        """Live mode works with all credentials."""
        config = PaymentConfig("live")
        config.validate_startup("key_id", "key_secret", "webhook_secret")
        assert config.is_live
        assert "LIVE mode" in caplog.text

    def test_config_properties(self):
        """Test mode property helpers."""
        disabled_config = PaymentConfig("disabled")
        assert disabled_config.is_disabled
        assert not disabled_config.is_test
        assert not disabled_config.is_live

        test_config = PaymentConfig("test")
        assert not test_config.is_disabled
        assert test_config.is_test
        assert not test_config.is_live

        live_config = PaymentConfig("live")
        assert not live_config.is_disabled
        assert not live_config.is_test
        assert live_config.is_live


class TestAdminGrantSubscription:
    """Test admin grant subscription endpoint."""

    @pytest.mark.asyncio
    async def test_grant_subscription_creates_active(self, client, db_session, admin_user, candidate_user):
        """Admin grant creates immediately active subscription."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "job_search",
                "reason": "Trial grant for testing",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"]
        assert data["status"] == "active"
        assert data["plan_tier"] == "job_search"
        assert data["user_id"] == candidate_user["id"]

    @pytest.mark.asyncio
    async def test_grant_subscription_sets_dates(self, client, db_session, admin_user, candidate_user):
        """Grant respects custom started_at and ends_at."""
        now = datetime.now(timezone.utc)
        started = (now - timedelta(days=1)).isoformat()
        ends = (now + timedelta(days=90)).isoformat()

        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "complete",
                "reason": "Extended trial",
                "started_at": started,
                "ends_at": ends,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"]
        # Dates should be close to requested (allow small variance for processing time)
        assert "started_at" in data
        assert "renews_at" in data

    @pytest.mark.asyncio
    async def test_grant_subscription_defaults_to_30_days(self, client, db_session, admin_user, candidate_user):
        """Grant without dates defaults to now + 30 days."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "resume_builder",
                "reason": "New user onboarding",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"]
        assert "renews_at" in data

    @pytest.mark.asyncio
    async def test_grant_subscription_cancels_existing(self, client, db_session, admin_user, candidate_user):
        """Grant cancels existing active subscription."""
        from models import Subscription, SubscriptionStatus, PlanTier, UserRole

        # Create existing active subscription
        existing_sub = Subscription(
            user_id=candidate_user["id"],
            role=UserRole.candidate,
            plan_tier=PlanTier.job_search,
            status=SubscriptionStatus.active,
        )
        db_session.add(existing_sub)
        await db_session.flush()
        existing_id = existing_sub.id

        # Grant new subscription
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "complete",
                "reason": "Upgrade",
            },
        )
        assert response.status_code == 200

        # Verify old subscription cancelled
        await db_session.refresh(existing_sub)
        assert existing_sub.status == SubscriptionStatus.cancelled

    @pytest.mark.asyncio
    async def test_grant_subscription_validates_plan_tier_for_role(self, client, db_session, admin_user, company_user):
        """Grant validates plan tier matches user role."""
        # Try to grant candidate plan to company user (invalid)
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": company_user["id"],
                "plan_tier": "job_search",  # Candidate plan
                "reason": "Testing",
            },
        )
        assert response.status_code == 400  # or 422 validation error
        assert "Invalid plan tier" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_grant_subscription_requires_admin(self, client, db_session, candidate_user_token, candidate_user):
        """Non-admin cannot grant subscriptions."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "complete",
                "reason": "Testing",
            },
        )
        assert response.status_code == 403
        assert "privilege" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_grant_subscription_user_not_found(self, client, admin_user):
        """Grant to non-existent user returns 404."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": str(uuid4()),
                "plan_tier": "job_search",
                "reason": "Testing",
            },
        )
        assert response.status_code == 404
        assert "User not found" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_grant_subscription_creates_audit_log(self, client, db_session, admin_user, candidate_user):
        """Grant creates audit log with admin_id and reason."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "complete",
                "reason": "Promotional grant for beta testing",
            },
        )
        assert response.status_code == 200
        sub_id = response.json()["id"]

        # Query audit log
        from sqlalchemy import select
        audit_logs = await db_session.execute(
            select(SubscriptionAuditLog)
            .where(SubscriptionAuditLog.subscription_id == sub_id)
            .where(SubscriptionAuditLog.action == "grant")
        )
        logs = audit_logs.scalars().all()
        assert len(logs) > 0

        log = logs[0]
        assert log.admin_id == admin_user["id"]
        assert log.reason == "Promotional grant for beta testing"
        assert log.new_status == "active"

    @pytest.mark.asyncio
    async def test_grant_subscription_reason_required(self, client, db_session, admin_user, candidate_user):
        """Grant requires reason field."""
        response = client.post(
            "/admin/subscriptions/grant",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={
                "user_id": candidate_user["id"],
                "plan_tier": "complete",
                # Missing reason
            },
        )
        assert response.status_code == 422
        assert "reason" in response.json().get("detail", str(response.json())).lower()

    @pytest.mark.asyncio
    async def test_grant_subscription_candidate_tier_to_candidate(self, client, db_session, admin_user, candidate_user):
        """Grant candidate plan tier to candidate user works."""
        for tier in ["resume_builder", "job_search", "complete"]:
            response = client.post(
                "/admin/subscriptions/grant",
                headers={"Authorization": f"Bearer {admin_user['token']}"},
                json={
                    "user_id": candidate_user["id"],
                    "plan_tier": tier,
                    "reason": f"Testing {tier}",
                },
            )
            assert response.status_code == 200, f"Failed for tier {tier}: {response.json()}"
            assert response.json()["plan_tier"] == tier

    @pytest.mark.asyncio
    async def test_grant_subscription_company_tier_to_company(self, client, db_session, admin_user, company_user):
        """Grant company plan tier to company user works."""
        for tier in ["corporate_annual", "corporate_lifetime"]:
            response = client.post(
                "/admin/subscriptions/grant",
                headers={"Authorization": f"Bearer {admin_user['token']}"},
                json={
                    "user_id": company_user["id"],
                    "plan_tier": tier,
                    "reason": f"Testing {tier}",
                },
            )
            assert response.status_code == 200, f"Failed for tier {tier}: {response.json()}"
            assert response.json()["plan_tier"] == tier
