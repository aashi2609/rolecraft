"""Step 6D: Payment service for Razorpay integration.

Handles:
- Creating payment orders
- Verifying payment signatures
- Processing webhooks (idempotent)
- Updating subscription status on successful payment
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    BillingPeriod,
    PaymentStatus,
    PaymentTransaction,
    PlanTier,
    PricePoint,
    Subscription,
    SubscriptionStatus,
    User,
)
from services.subscription_service import log_subscription_change

logger = logging.getLogger(__name__)


class PaymentService:
    """Razorpay payment service."""

    def __init__(
        self,
        razorpay_key_id: Optional[str],
        razorpay_key_secret: Optional[str],
        razorpay_webhook_secret: Optional[str],
    ):
        self.key_id = razorpay_key_id
        self.key_secret = razorpay_key_secret
        self.webhook_secret = razorpay_webhook_secret

    async def create_order(
        self,
        db,
        user: User,
        plan_tier: PlanTier,
        billing_period: BillingPeriod,
        idempotency_key: Optional[str] = None,
    ) -> PaymentTransaction:
        """Create a payment order for a subscription plan.

        Args:
            db: Database session
            user: User making the payment
            plan_tier: Plan tier to subscribe to
            billing_period: Billing period (monthly, annual, etc.)
            idempotency_key: Optional idempotency key for replay protection

        Returns:
            PaymentTransaction with Razorpay order_id

        Raises:
            ValueError: If price point not found or user is invalid
        """
        # Get price point for this plan/period
        price_point = await db.scalar(
            select(PricePoint).where(
                PricePoint.plan_tier == plan_tier,
                PricePoint.billing_period == billing_period,
                PricePoint.active == True,
            )
        )
        if not price_point:
            raise ValueError(
                f"No active pricing for {plan_tier.value}/{billing_period.value}"
            )

        # Check for idempotency (if key provided)
        if idempotency_key:
            existing = await db.scalar(
                select(PaymentTransaction).where(
                    PaymentTransaction.idempotency_key == idempotency_key,
                    PaymentTransaction.user_id == user.id,
                )
            )
            if existing:
                return existing  # Return existing transaction

        # Create Razorpay order ID (mock for test mode, real API in live)
        razorpay_order_id = self._generate_order_id()

        # Create payment transaction
        transaction = PaymentTransaction(
            user_id=user.id,
            price_point_id=price_point.id,
            amount_paise=price_point.amount_paise,
            razorpay_order_id=razorpay_order_id,
            status=PaymentStatus.pending,
            idempotency_key=idempotency_key,
        )
        db.add(transaction)
        await db.flush()

        logger.info(
            f"Created payment order {razorpay_order_id} for user {user.id}, amount {transaction.amount_rupees} INR"
        )

        return transaction

    def _generate_order_id(self) -> str:
        """Generate a Razorpay-style order ID."""
        import uuid as uuid_module

        return f"order_{uuid_module.uuid4().hex[:16]}"

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify Razorpay payment signature (HMAC-SHA256).

        Args:
            razorpay_order_id: Order ID from payment response
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay webhook/response

        Returns:
            True if signature is valid, False otherwise

        Raises:
            RuntimeError: If webhook secret not configured
        """
        if not self.webhook_secret:
            raise RuntimeError("Webhook secret not configured")

        # Create signature message: order_id|payment_id
        message = f"{razorpay_order_id}|{razorpay_payment_id}"

        # Calculate expected signature using webhook secret
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(expected_signature, razorpay_signature)

        if not is_valid:
            logger.warning(
                f"Invalid signature for order {razorpay_order_id}: "
                f"expected {expected_signature}, got {razorpay_signature}"
            )

        return is_valid

    async def process_webhook(
        self,
        db,
        webhook_data: dict,
        event_type: str,
    ) -> Optional[PaymentTransaction]:
        """Process Razorpay webhook (idempotent).

        Supported events:
        - payment.authorized: Payment successful
        - payment.failed: Payment failed

        Args:
            db: Database session
            webhook_data: Full webhook payload from Razorpay
            event_type: Event type (payment.authorized, etc.)

        Returns:
            PaymentTransaction if processed, None if skipped

        Raises:
            ValueError: If webhook data is invalid
        """
        if event_type == "payment.authorized":
            return await self._handle_payment_authorized(db, webhook_data)
        elif event_type == "payment.failed":
            return await self._handle_payment_failed(db, webhook_data)
        else:
            logger.info(f"Ignoring webhook event: {event_type}")
            return None

    async def _handle_payment_authorized(
        self, db, webhook_data: dict
    ) -> PaymentTransaction:
        """Handle payment.authorized webhook."""
        payment_data = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})

        razorpay_payment_id = payment_data.get("id")
        razorpay_order_id = payment_data.get("order_id")

        if not razorpay_order_id:
            raise ValueError("No order_id in webhook data")

        # Find or create transaction
        transaction = await db.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.razorpay_order_id == razorpay_order_id
            )
        )

        if not transaction:
            raise ValueError(f"No transaction for order {razorpay_order_id}")

        # Idempotency: if already completed, return
        if transaction.status == PaymentStatus.completed:
            logger.info(f"Transaction {razorpay_order_id} already completed, skipping")
            return transaction

        # Update transaction status
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.status = PaymentStatus.completed
        transaction.webhook_data = webhook_data
        transaction.webhook_received_at = datetime.now(timezone.utc)
        transaction.completed_at = datetime.now(timezone.utc)

        # Create pending subscription (will be activated by webhook)
        if not transaction.subscription_id:
            # Get user and price point
            user = await db.get(User, transaction.user_id)
            price_point = await db.get(PricePoint, transaction.price_point_id)

            if not user or not price_point:
                raise ValueError("User or price point not found")

            # Determine subscription end date based on billing period
            started_at = datetime.now(timezone.utc)
            if price_point.billing_period == BillingPeriod.monthly:
                ends_at = started_at + timedelta(days=30)
            elif price_point.billing_period == BillingPeriod.quarterly:
                ends_at = started_at + timedelta(days=90)
            elif price_point.billing_period == BillingPeriod.annual:
                ends_at = started_at + timedelta(days=365)
            elif price_point.billing_period == BillingPeriod.lifetime:
                ends_at = None  # No renewal for lifetime
            else:
                ends_at = started_at + timedelta(days=30)

            # Create subscription with status=active (payment verified)
            sub = Subscription(
                user_id=transaction.user_id,
                role=user.role,
                plan_tier=price_point.plan_tier,
                status=SubscriptionStatus.active,
                started_at=started_at,
                renews_at=ends_at,
            )
            db.add(sub)
            await db.flush()
            transaction.subscription_id = sub.id

            # Log the activation
            await log_subscription_change(
                db,
                subscription_id=sub.id,
                user_id=user.id,
                action="activate_via_payment",
                new_plan_tier=price_point.plan_tier.value,
                new_status=SubscriptionStatus.active.value,
                payment_transaction_id=str(transaction.id),
                reason=f"Payment verified: {price_point.amount_rupees} INR via Razorpay",
            )

            logger.info(
                f"Created subscription {sub.id} for user {user.id} after payment {razorpay_payment_id}"
            )

        await db.flush()
        return transaction

    async def _handle_payment_failed(
        self, db, webhook_data: dict
    ) -> PaymentTransaction:
        """Handle payment.failed webhook."""
        payment_data = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})

        razorpay_payment_id = payment_data.get("id")
        razorpay_order_id = payment_data.get("order_id")
        error_reason = payment_data.get("error_reason", "Unknown error")

        if not razorpay_order_id:
            raise ValueError("No order_id in webhook data")

        # Find transaction
        transaction = await db.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.razorpay_order_id == razorpay_order_id
            )
        )

        if not transaction:
            raise ValueError(f"No transaction for order {razorpay_order_id}")

        # Idempotency: if already failed, return
        if transaction.status == PaymentStatus.failed:
            logger.info(f"Transaction {razorpay_order_id} already marked failed, skipping")
            return transaction

        # Update transaction status
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.status = PaymentStatus.failed
        transaction.failure_reason = error_reason
        transaction.webhook_data = webhook_data
        transaction.webhook_received_at = datetime.now(timezone.utc)

        logger.warning(
            f"Payment failed for order {razorpay_order_id}: {error_reason}"
        )

        await db.flush()
        return transaction

    def get_order_creation_payload(
        self,
        amount_paise: int,
        razorpay_order_id: str,
        user_email: str,
    ) -> dict:
        """Get payload for client-side Razorpay.Checkout.open().

        Args:
            amount_paise: Amount in paise
            razorpay_order_id: Order ID from payment transaction
            user_email: User email for Razorpay

        Returns:
            Dict with keys: key, amount, order_id, email
        """
        return {
            "key": self.key_id,
            "amount": amount_paise,
            "order_id": razorpay_order_id,
            "email": user_email,
        }
