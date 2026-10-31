"""Step 6D: Real payments integration tests.

Tests verify:
- Payment order creation with pricing
- Signature verification (HMAC-SHA256)
- Webhook processing (idempotent)
- Subscription activation on successful payment
- Error handling (payment failed, invalid signatures)
- Idempotency keys prevent duplicate charges
"""

import pytest
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from models import (
    BillingPeriod,
    PaymentStatus,
    PaymentTransaction,
    PricePoint,
    PlanTier,
    SubscriptionStatus,
    UserRole,
)


class TestPricePoints:
    """Test pricing table and lookups."""

    @pytest.mark.asyncio
    async def test_price_point_creation(self, db_session):
        """Create a price point for a plan/period."""
        price_point = PricePoint(
            plan_tier=PlanTier.job_search,
            billing_period=BillingPeriod.annual,
            amount_paise=99900,  # ₹999
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.flush()

        assert price_point.amount_rupees == 999.0
        assert price_point.active

    @pytest.mark.asyncio
    async def test_price_point_unique_constraint(self, db_session):
        """Can't create duplicate plan/period combinations."""
        from sqlalchemy import select

        price_point1 = PricePoint(
            plan_tier=PlanTier.complete,
            billing_period=BillingPeriod.monthly,
            amount_paise=49900,
            currency="INR",
        )
        db_session.add(price_point1)
        await db_session.flush()

        price_point2 = PricePoint(
            plan_tier=PlanTier.complete,
            billing_period=BillingPeriod.monthly,
            amount_paise=59900,  # Different price
            currency="INR",
        )
        db_session.add(price_point2)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_price_point_rupees_conversion(self, db_session):
        """Amount in paise converts to rupees correctly."""
        price_point = PricePoint(
            plan_tier=PlanTier.resume_builder,
            billing_period=BillingPeriod.monthly,
            amount_paise=29900,
            currency="INR",
        )
        db_session.add(price_point)
        await db_session.flush()

        assert price_point.amount_rupees == 299.0


class TestPaymentOrderCreation:
    """Test payment order endpoint."""

    @pytest.mark.asyncio
    async def test_create_payment_order(
        self, client, db_session, candidate_user, candidate_user_token
    ):
        """Create payment order for a subscription plan."""
        # Create price point first
        price_point = PricePoint(
            plan_tier=PlanTier.job_search,
            billing_period=BillingPeriod.annual,
            amount_paise=99900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.commit()

        # Create order
        response = client.post(
            "/payments/orders",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "plan_tier": "job_search",
                "billing_period": "annual",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["order_id"]
        assert data["key"]
        assert data["amount"] == 99900
        assert data["email"] == candidate_user["email"]
        assert data["currency"] == "INR"

    @pytest.mark.asyncio
    async def test_create_payment_order_idempotency(
        self, client, db_session, candidate_user, candidate_user_token
    ):
        """Same idempotency key returns same order."""
        # Create price point
        price_point = PricePoint(
            plan_tier=PlanTier.complete,
            billing_period=BillingPeriod.monthly,
            amount_paise=49900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.commit()

        idempotency_key = str(uuid4())

        # Create first order
        response1 = client.post(
            "/payments/orders",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "plan_tier": "complete",
                "billing_period": "monthly",
                "idempotency_key": idempotency_key,
            },
        )
        assert response1.status_code == 200
        order1 = response1.json()

        # Create second order with same key
        response2 = client.post(
            "/payments/orders",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "plan_tier": "complete",
                "billing_period": "monthly",
                "idempotency_key": idempotency_key,
            },
        )
        assert response2.status_code == 200
        order2 = response2.json()

        # Same order ID returned
        assert order1["order_id"] == order2["order_id"]

    @pytest.mark.asyncio
    async def test_create_payment_order_missing_price_point(
        self, client, candidate_user_token
    ):
        """Creating order for non-existent pricing fails."""
        response = client.post(
            "/payments/orders",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "plan_tier": "job_search",
                "billing_period": "quarterly",  # Not configured
            },
        )
        assert response.status_code == 400
        assert "No active pricing" in response.json().get("detail", "")


class TestSignatureVerification:
    """Test Razorpay signature verification."""

    def test_verify_signature_valid(self):
        """Valid HMAC-SHA256 signature verifies."""
        from services.payment_service import PaymentService

        webhook_secret = "test_webhook_secret_123"
        service = PaymentService(None, None, webhook_secret)

        order_id = "order_test123"
        payment_id = "pay_test456"

        # Calculate signature
        message = f"{order_id}|{payment_id}"
        signature = hmac.new(
            webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Verify
        is_valid = service.verify_payment_signature(order_id, payment_id, signature)
        assert is_valid

    def test_verify_signature_invalid(self):
        """Invalid signature fails verification."""
        from services.payment_service import PaymentService

        webhook_secret = "test_webhook_secret_123"
        service = PaymentService(None, None, webhook_secret)

        order_id = "order_test123"
        payment_id = "pay_test456"
        bad_signature = "0" * 64  # Invalid signature

        is_valid = service.verify_payment_signature(
            order_id, payment_id, bad_signature
        )
        assert not is_valid

    def test_verify_signature_replay_protection(self):
        """Modified message fails verification."""
        from services.payment_service import PaymentService

        webhook_secret = "test_webhook_secret_123"
        service = PaymentService(None, None, webhook_secret)

        order_id = "order_test123"
        payment_id = "pay_test456"

        # Calculate signature for original
        message = f"{order_id}|{payment_id}"
        signature = hmac.new(
            webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Try to use for different payment ID
        is_valid = service.verify_payment_signature(
            order_id, "pay_different", signature
        )
        assert not is_valid


class TestWebhookProcessing:
    """Test webhook processing (idempotent)."""

    @pytest.mark.asyncio
    async def test_process_payment_authorized_webhook(
        self, client, db_session, candidate_user
    ):
        """Process payment.authorized webhook (idempotent)."""
        from sqlalchemy import select

        # Create price point and transaction
        price_point = PricePoint(
            plan_tier=PlanTier.job_search,
            billing_period=BillingPeriod.annual,
            amount_paise=99900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.flush()

        order_id = "order_test123"
        transaction = PaymentTransaction(
            user_id=candidate_user["id"],
            price_point_id=price_point.id,
            amount_paise=99900,
            razorpay_order_id=order_id,
            status=PaymentStatus.pending,
        )
        db_session.add(transaction)
        await db_session.commit()

        # Send webhook
        webhook_data = {
            "event": "payment.authorized",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test456",
                        "order_id": order_id,
                    }
                }
            },
        }

        response = client.post("/payments/webhook", json=webhook_data)
        assert response.status_code == 200

        # Verify transaction updated
        await db_session.refresh(transaction)
        assert transaction.status == PaymentStatus.completed
        assert transaction.razorpay_payment_id == "pay_test456"

        # Verify subscription created
        subs = await db_session.execute(
            select(Subscription).where(Subscription.user_id == candidate_user["id"])
        )
        sub = subs.scalars().first()
        assert sub is not None
        assert sub.status == SubscriptionStatus.active
        assert sub.plan_tier == PlanTier.job_search

    @pytest.mark.asyncio
    async def test_process_payment_authorized_webhook_idempotent(
        self, client, db_session, candidate_user
    ):
        """Processing same webhook twice is safe (idempotent)."""
        # Create price point and transaction
        price_point = PricePoint(
            plan_tier=PlanTier.complete,
            billing_period=BillingPeriod.monthly,
            amount_paise=49900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.flush()

        order_id = "order_test789"
        transaction = PaymentTransaction(
            user_id=candidate_user["id"],
            price_point_id=price_point.id,
            amount_paise=49900,
            razorpay_order_id=order_id,
            status=PaymentStatus.pending,
        )
        db_session.add(transaction)
        await db_session.commit()

        webhook_data = {
            "event": "payment.authorized",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test999",
                        "order_id": order_id,
                    }
                }
            },
        }

        # Process twice
        response1 = client.post("/payments/webhook", json=webhook_data)
        assert response1.status_code == 200

        response2 = client.post("/payments/webhook", json=webhook_data)
        assert response2.status_code == 200

        # Still only one subscription created
        from sqlalchemy import func, select

        count = await db_session.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.user_id == candidate_user["id"]
            )
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_process_payment_failed_webhook(
        self, client, db_session, candidate_user
    ):
        """Process payment.failed webhook."""
        # Create transaction
        price_point = PricePoint(
            plan_tier=PlanTier.resume_builder,
            billing_period=BillingPeriod.monthly,
            amount_paise=29900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.flush()

        order_id = "order_fail123"
        transaction = PaymentTransaction(
            user_id=candidate_user["id"],
            price_point_id=price_point.id,
            amount_paise=29900,
            razorpay_order_id=order_id,
            status=PaymentStatus.pending,
        )
        db_session.add(transaction)
        await db_session.commit()

        # Send failure webhook
        webhook_data = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail456",
                        "order_id": order_id,
                        "error_reason": "Card declined",
                    }
                }
            },
        }

        response = client.post("/payments/webhook", json=webhook_data)
        assert response.status_code == 200

        # Verify transaction marked as failed
        await db_session.refresh(transaction)
        assert transaction.status == PaymentStatus.failed
        assert transaction.failure_reason == "Card declined"


class TestPaymentVerification:
    """Test payment verification endpoint."""

    @pytest.mark.asyncio
    async def test_verify_payment_with_valid_signature(
        self, client, db_session, candidate_user, candidate_user_token
    ):
        """Verify payment with valid signature."""
        from services.payment_service import PaymentService

        # Create price point and transaction
        price_point = PricePoint(
            plan_tier=PlanTier.job_search,
            billing_period=BillingPeriod.annual,
            amount_paise=99900,
            currency="INR",
            active=True,
        )
        db_session.add(price_point)
        await db_session.flush()

        order_id = "order_verify123"
        transaction = PaymentTransaction(
            user_id=candidate_user["id"],
            price_point_id=price_point.id,
            amount_paise=99900,
            razorpay_order_id=order_id,
            status=PaymentStatus.pending,
        )
        db_session.add(transaction)
        await db_session.commit()

        # Generate valid signature
        payment_id = "pay_verify456"
        webhook_secret = "test_secret"
        message = f"{order_id}|{payment_id}"
        signature = hmac.new(
            webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Verify payment
        response = client.post(
            "/payments/verify",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": signature,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"]
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_verify_payment_with_invalid_signature(
        self, client, candidate_user_token
    ):
        """Verify payment with invalid signature fails."""
        response = client.post(
            "/payments/verify",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "order_id": "order_123",
                "payment_id": "pay_456",
                "signature": "0" * 64,  # Invalid
            },
        )
        assert response.status_code == 400
        assert "Invalid payment signature" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_verify_payment_transaction_not_found(
        self, client, candidate_user_token
    ):
        """Verify payment for non-existent transaction fails."""
        import hmac
        import hashlib

        order_id = "order_nonexistent"
        payment_id = "pay_123"
        webhook_secret = "test_secret"
        message = f"{order_id}|{payment_id}"
        signature = hmac.new(
            webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/payments/verify",
            headers={"Authorization": f"Bearer {candidate_user_token}"},
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": signature,
            },
        )
        assert response.status_code == 404
        assert "Transaction not found" in response.json().get("detail", "")
