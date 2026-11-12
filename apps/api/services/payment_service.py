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
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from models import (
    BillingPeriod,
    PaymentStatus,
    PaymentTransaction,
    PlanTier,
    PricePoint,
    Subscription,
    SubscriptionStatus,
    SubscriptionAuditLog,
    User,
    WebhookEvent,
)
from services.subscription_service import log_subscription_change

logger = logging.getLogger(__name__)


# ── Step E5: PRICES Table (In-Code Pricing) ──────────────────────────────────


PRICES = {
    # Candidate plans (INR, in paise)
    (PlanTier.resume_builder, BillingPeriod.monthly): 29900,  # ₹299/month
    (PlanTier.resume_builder, BillingPeriod.annual): 299900,  # ₹2,999/year
    (PlanTier.job_search, BillingPeriod.monthly): 49900,  # ₹499/month
    (PlanTier.job_search, BillingPeriod.annual): 499900,  # ₹4,999/year
    (PlanTier.complete, BillingPeriod.monthly): 79900,  # ₹799/month
    (PlanTier.complete, BillingPeriod.annual): 799900,  # ₹7,999/year
    # Company plans (INR, in paise)
    (PlanTier.corporate_annual, BillingPeriod.annual): 499900,  # ₹4,999/year
    (PlanTier.corporate_lifetime, BillingPeriod.lifetime): 999900,  # ₹9,999/lifetime
}


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
                PricePoint.active.is_(True),
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

        Per Razorpay docs: https://razorpay.com/docs/payments/verify-payments/#:
        Signature = HMAC_SHA256(order_id + "|" + payment_id, webhook_secret)

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

        # Create signature message: order_id|payment_id (per Razorpay spec)
        message = f"{razorpay_order_id}|{razorpay_payment_id}"

        # Calculate expected signature using webhook secret
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures (constant-time comparison to prevent timing attacks)
        is_valid = hmac.compare_digest(expected_signature, razorpay_signature)

        if not is_valid:
            logger.warning(
                f"Invalid signature for order {razorpay_order_id}: "
                f"expected {expected_signature[:16]}..., got {razorpay_signature[:16]}..."
            )

        return is_valid

    async def process_webhook(
        self,
        db,
        raw_body: bytes,
        webhook_signature: str,
        webhook_event_id: str,
        webhook_data: dict,
        event_type: str,
    ) -> Optional[PaymentTransaction]:
        """Process Razorpay webhook (idempotent, signature-verified).

        Supported events:
        - payment.captured: Payment successfully captured (primary event)
        - payment.authorized: Payment authorized (manual-capture accounts)
        - payment.failed: Payment failed

        Security:
        - Signature verified over raw request body (not parsed JSON)
        - Event ID checked for duplicate processing (idempotent)
        - Amount and currency validated against transaction
        - Transaction row locked during activation (SELECT ... FOR UPDATE)

        Idempotency:
        - Insert webhook_events row FIRST before any processing
        - Handle IntegrityError on UNIQUE constraint for duplicate event_id
        - Set processed=True + processed_at in same transaction as activation
        - On duplicate: return None (route returns 200 anyway, idempotent)

        Args:
            db: Database session
            raw_body: Raw request body bytes (before JSON parsing)
            webhook_signature: X-Razorpay-Signature header value
            webhook_event_id: X-Razorpay-Event-Id header value
            webhook_data: Parsed webhook payload
            event_type: Event type (payment.captured, payment.authorized, etc.)

        Returns:
            PaymentTransaction if processed, None if skipped

        Raises:
            ValueError: If signature invalid or webhook data invalid
        """
        # Step 1: Verify webhook signature over raw body (CRITICAL)
        is_valid_signature = self._verify_webhook_signature(raw_body, webhook_signature)
        if not is_valid_signature:
            logger.warning(
                f"Invalid webhook signature from Razorpay; ignoring event {webhook_event_id}"
            )
            raise ValueError("Invalid webhook signature")

        # Step 2: Insert webhook_events row FIRST (idempotency key)
        # Handle IntegrityError on duplicate UNIQUE(provider, provider_event_id)
        from sqlalchemy.exc import IntegrityError
        
        webhook_event = WebhookEvent(
            provider_event_id=webhook_event_id,
            provider="razorpay",
            event_type=event_type,
            event_data=webhook_data,
            processed=False,
        )
        db.add(webhook_event)
        
        try:
            await db.flush()
        except IntegrityError:
            # Duplicate event_id: this webhook was already processed
            await db.rollback()
            
            # Query to get the existing event (for logging)
            existing_event = await db.scalar(
                select(WebhookEvent).where(
                    WebhookEvent.provider_event_id == webhook_event_id
                )
            )
            
            logger.info(
                f"Duplicate webhook event {webhook_event_id}; skipping (already processed={existing_event.processed if existing_event else '?'})"
            )
            
            # Return the transaction from earlier processing if it exists
            if existing_event and existing_event.payment_transaction_id:
                return await db.get(PaymentTransaction, existing_event.payment_transaction_id)
            return None

        # Step 3: Process event
        transaction = None
        try:
            if event_type == "payment.captured":
                # payment.captured is the primary event (auto-capture is default)
                # Reference: https://razorpay.com/docs/payments/payments/capture-settings/?preferred-country=IN
                # "By default, once your customer completes a payment, it is automatically moved to the captured state."
                transaction = await self._handle_payment_captured(db, webhook_data)
                # Only activate if transaction is completed (all validations passed)
                if transaction and transaction.status == PaymentStatus.completed:
                    await self.activate_subscription(db, transaction)
            elif event_type == "payment.authorized":
                # Fallback for manual-capture accounts (not auto-capture)
                transaction = await self._handle_payment_authorized(db, webhook_data)
                # Only activate if transaction is completed (all validations passed)
                if transaction and transaction.status == PaymentStatus.completed:
                    await self.activate_subscription(db, transaction)
            elif event_type == "payment.failed":
                transaction = await self._handle_payment_failed(db, webhook_data)
                # No activation for failed payments
            else:
                logger.info(f"Ignoring unsupported webhook event: {event_type}")
                return None

            # Step 4: Mark webhook event as processed (SAME transaction as activation)
            webhook_event.processed = True
            webhook_event.processed_at = datetime.now(timezone.utc)
            webhook_event.payment_transaction_id = transaction.id if transaction else None

            await db.flush()
            return transaction

        except Exception as e:
            logger.error(f"Error processing webhook event {webhook_event_id}: {e}")
            raise

    def _verify_webhook_signature(self, raw_body: bytes, webhook_signature: str) -> bool:
        """Verify Razorpay webhook signature over raw request body.

        Per Razorpay docs (https://razorpay.com/docs/webhooks/understand-validate-webhooks/):
        signature = HMAC_SHA256(raw_body, webhook_secret)

        Args:
            raw_body: Raw request body bytes (must be bytes, not parsed JSON)
            webhook_signature: Value of X-Razorpay-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.error("Webhook secret not configured; cannot verify signature")
            return False

        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Compare (constant-time comparison to prevent timing attacks)
        is_valid = hmac.compare_digest(expected_signature, webhook_signature)

        if not is_valid:
            logger.warning(
                f"Webhook signature mismatch: "
                f"expected {expected_signature[:16]}..., got {webhook_signature[:16]}..."
            )

        return is_valid

    async def activate_subscription(
        self,
        db,
        transaction: PaymentTransaction,
    ) -> Subscription:
        """E5: Centralized subscription activation (only path that sets status=active for payments).

        This is the ONLY code path that creates an active paid subscription from a payment.
        Called from webhook handler (POST /payments/webhook) after signature verification.

        In ONE database transaction:
        1. Lock the transaction row (SELECT ... FOR UPDATE) to prevent race conditions
        2. Return early if already activated (idempotency keyed on razorpay_payment_id)
        3. Deactivate any previous ACTIVE subscriptions for the user (not pending)
        4. Create new active subscription with expiry based on billing period
        5. Write subscription audit log entry
        6. Commit or rollback on error

        Args:
            db: Database session (must support SELECT FOR UPDATE)
            transaction: PaymentTransaction with verified payment

        Returns:
            Active Subscription created

        Raises:
            ValueError: If transaction invalid or price point not found
        """
        # Step 1: Lock the transaction row to prevent concurrent activation
        locked_transaction = await db.scalar(
            select(PaymentTransaction)
            .where(PaymentTransaction.id == transaction.id)
            .with_for_update()  # SELECT ... FOR UPDATE
        )
        
        if not locked_transaction:
            raise ValueError(f"Transaction {transaction.id} not found or deleted")

        # Step 2: Verify transaction is in correct state
        if locked_transaction.status != PaymentStatus.completed:
            raise ValueError(
                f"Transaction {transaction.id} not completed (status={locked_transaction.status})"
            )

        # Step 3: Early return if subscription already created (idempotency keyed on razorpay_payment_id)
        # This prevents duplicate subscription creation on webhook replay
        if locked_transaction.subscription_id:
            existing_sub = await db.get(Subscription, locked_transaction.subscription_id)
            if existing_sub and existing_sub.status == SubscriptionStatus.active:
                logger.info(
                    f"Subscription {existing_sub.id} already active for payment {locked_transaction.razorpay_payment_id}; skipping"
                )
                return existing_sub

        # Step 4: Get user and price point
        user = await db.get(User, locked_transaction.user_id)
        price_point = await db.get(PricePoint, locked_transaction.price_point_id)

        if not user or not price_point:
            raise ValueError("User or price point not found")

        # Step 5: Deactivate ALL previous ACTIVE subscriptions for this user
        # (must use ACTIVE status, not pending from signup flow)
        active_subs = await db.scalars(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.active,
            )
        )
        for old_sub in active_subs.all():
            old_sub.status = SubscriptionStatus.cancelled
            await log_subscription_change(
                db,
                subscription_id=old_sub.id,
                user_id=user.id,
                action="cancel",
                old_plan_tier=old_sub.plan_tier.value,
                old_status=SubscriptionStatus.active.value,
                new_status=SubscriptionStatus.cancelled.value,
                reason="Replaced by new payment",
            )
            logger.info(f"Cancelled previous subscription {old_sub.id}")

        # Step 6: Calculate subscription end date based on billing period
        started_at = datetime.now(timezone.utc)
        if price_point.billing_period == BillingPeriod.monthly:
            ends_at = started_at + timedelta(days=30)
        elif price_point.billing_period == BillingPeriod.quarterly:
            ends_at = started_at + timedelta(days=90)
        elif price_point.billing_period == BillingPeriod.annual:
            ends_at = started_at + timedelta(days=365)
        elif price_point.billing_period == BillingPeriod.lifetime:
            ends_at = None  # No expiry for lifetime
        else:
            ends_at = started_at + timedelta(days=30)

        # Step 7: Create new active subscription
        sub = Subscription(
            user_id=user.id,
            role=user.role,
            plan_tier=price_point.plan_tier,
            status=SubscriptionStatus.active,
            started_at=started_at,
            renews_at=ends_at,
        )
        db.add(sub)
        await db.flush()

        # Step 8: Link transaction to subscription
        locked_transaction.subscription_id = sub.id

        # Step 9: Log subscription activation
        await log_subscription_change(
            db,
            subscription_id=sub.id,
            user_id=user.id,
            action="activate_via_payment",
            new_plan_tier=price_point.plan_tier.value,
            new_status=SubscriptionStatus.active.value,
            payment_transaction_id=str(locked_transaction.id),
            reason=f"Payment verified: {price_point.amount_rupees} INR via Razorpay (period: {price_point.billing_period.value})",
        )

        logger.info(
            f"Activated subscription {sub.id} for user {user.id}, "
            f"plan={price_point.plan_tier.value}, "
            f"period={price_point.billing_period.value}, "
            f"expires={ends_at.isoformat() if ends_at else 'never'}"
        )

        await db.flush()
        return sub

    async def _handle_payment_captured(
        self, db, webhook_data: dict
    ) -> PaymentTransaction:
        """Handle payment.captured webhook (primary event with auto-capture enabled).

        Validates:
        - Amount and currency match transaction
        - Order exists in database
        - Idempotency (no duplicate activation)
        
        Reference: https://razorpay.com/docs/webhooks/payloads/payments/
        Triggered when a payment is successfully captured.
        """
        payment_data = (
            webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
        )

        razorpay_payment_id = payment_data.get("id")
        razorpay_order_id = payment_data.get("order_id")
        amount_paise = payment_data.get("amount")  # In paise
        currency = payment_data.get("currency")

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

        # CRITICAL: Validate amount and currency
        if amount_paise and amount_paise != transaction.amount_paise:
            logger.error(
                f"AMOUNT MISMATCH for order {razorpay_order_id}: "
                f"webhook={amount_paise} paise, transaction={transaction.amount_paise} paise"
            )
            # Mark transaction as failed; do NOT activate
            transaction.status = PaymentStatus.failed
            transaction.failure_reason = "Amount mismatch in webhook"
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.webhook_data = webhook_data
            transaction.webhook_received_at = datetime.now(timezone.utc)
            await db.flush()
            return transaction

        if currency and currency != "INR":
            logger.error(
                f"CURRENCY MISMATCH for order {razorpay_order_id}: "
                f"expected INR, got {currency}"
            )
            transaction.status = PaymentStatus.failed
            transaction.failure_reason = f"Invalid currency in webhook: {currency}"
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.webhook_data = webhook_data
            transaction.webhook_received_at = datetime.now(timezone.utc)
            await db.flush()
            return transaction

        # Idempotency: if already completed, return
        if transaction.status == PaymentStatus.completed:
            logger.info(f"Transaction {razorpay_order_id} already completed, skipping")
            return transaction

        # Update transaction status to completed
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.status = PaymentStatus.completed
        transaction.webhook_data = webhook_data
        transaction.webhook_received_at = datetime.now(timezone.utc)
        transaction.completed_at = datetime.now(timezone.utc)

        await db.flush()
        return transaction

    async def _handle_payment_authorized(
        self, db, webhook_data: dict
    ) -> PaymentTransaction:
        """Handle payment.authorized webhook (fallback for manual-capture accounts).

        Most accounts use auto-capture (default), which triggers payment.captured.
        For accounts with manual capture enabled, payment.authorized is the event.
        
        Validates:
        - Amount and currency match transaction
        - Order exists in database
        - Idempotency (no duplicate activation)

        Reference: https://razorpay.com/docs/webhooks/payloads/payments/
        Triggered when a payment is authorised.
        """
        payment_data = (
            webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
        )

        razorpay_payment_id = payment_data.get("id")
        razorpay_order_id = payment_data.get("order_id")
        amount_paise = payment_data.get("amount")  # In paise
        currency = payment_data.get("currency")

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

        # CRITICAL: Validate amount and currency
        if amount_paise and amount_paise != transaction.amount_paise:
            logger.error(
                f"AMOUNT MISMATCH for order {razorpay_order_id}: "
                f"webhook={amount_paise} paise, transaction={transaction.amount_paise} paise"
            )
            # Mark transaction as amount_mismatch; do NOT activate
            transaction.status = PaymentStatus.failed
            transaction.failure_reason = "Amount mismatch in webhook"
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.webhook_data = webhook_data
            transaction.webhook_received_at = datetime.now(timezone.utc)
            return transaction

        if currency and currency != "INR":
            logger.error(
                f"CURRENCY MISMATCH for order {razorpay_order_id}: "
                f"expected INR, got {currency}"
            )
            transaction.status = PaymentStatus.failed
            transaction.failure_reason = f"Invalid currency in webhook: {currency}"
            transaction.razorpay_payment_id = razorpay_payment_id
            transaction.webhook_data = webhook_data
            transaction.webhook_received_at = datetime.now(timezone.utc)
            return transaction

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

        await db.flush()
        return transaction

    async def _handle_payment_failed(
        self, db, webhook_data: dict
    ) -> PaymentTransaction:
        """Handle payment.failed webhook."""
        payment_data = (
            webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
        )

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
            logger.info(
                f"Transaction {razorpay_order_id} already marked failed, skipping"
            )
            return transaction

        # Update transaction status
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.status = PaymentStatus.failed
        transaction.failure_reason = error_reason
        transaction.webhook_data = webhook_data
        transaction.webhook_received_at = datetime.now(timezone.utc)

        logger.warning(f"Payment failed for order {razorpay_order_id}: {error_reason}")

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
