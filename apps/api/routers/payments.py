"""Step 6D: Payment routes for Razorpay integration.

Endpoints:
- POST /payments/orders: Create payment order
- POST /payments/verify: Verify and process payment
- POST /payments/webhook: Handle Razorpay webhooks (idempotent)
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from core.dependencies import DbSession, get_current_user
from core.config import get_settings
from core.enum_utils import coerce_enum
from models import (
    BillingPeriod,
    PlanTier,
    PaymentTransaction,
    User,
    PaymentStatus,
)
from services.payment_service import PaymentService
from services.subscription_service import log_subscription_change

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()


# ── Schemas ──────────────────────────────────────────────────────────────────


class OrderCreateRequest(BaseModel):
    """Request to create a payment order."""

    plan_tier: PlanTier
    billing_period: BillingPeriod
    idempotency_key: Optional[str] = None

    @field_validator("plan_tier", mode="before")
    @classmethod
    def validate_plan_tier(cls, v: Any) -> PlanTier:
        return coerce_enum(PlanTier, v, "plan_tier", allow_none=False)

    @field_validator("billing_period", mode="before")
    @classmethod
    def validate_billing_period(cls, v: Any) -> BillingPeriod:
        return coerce_enum(BillingPeriod, v, "billing_period", allow_none=False)


class OrderCreateResponse(BaseModel):
    """Response with order details for client-side checkout."""

    order_id: str
    key: str
    amount: int  # in paise
    email: str
    currency: str = "INR"


class PaymentVerifyRequest(BaseModel):
    """Request to verify and process payment."""

    order_id: str
    payment_id: str
    signature: str


class PaymentVerifyResponse(BaseModel):
    """Response after payment verification."""

    ok: bool
    transaction_id: str
    subscription_id: Optional[str] = None
    status: str  # completed, failed
    message: str


class WebhookResponse(BaseModel):
    """Response to webhook."""

    ok: bool
    message: str


# ── Dependencies ──────────────────────────────────────────────────────────────


def get_payment_service() -> PaymentService:
    """Get payment service with credentials."""
    return PaymentService(
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_key_secret=settings.razorpay_key_secret,
        razorpay_webhook_secret=settings.razorpay_webhook_secret,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/orders", response_model=OrderCreateResponse)
async def create_order(
    request: OrderCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> Any:
    """Create a Razorpay payment order.

    Request body:
    {
      "plan_tier": "complete",
      "billing_period": "annual",
      "idempotency_key": "optional-uuid"
    }

    Response:
    {
      "order_id": "order_xyz...",
      "key": "rzp_live_...",
      "amount": 99900,
      "email": "user@example.com",
      "currency": "INR"
    }

    Client uses this to initialize Razorpay.Checkout:
    ```
    const options = {
      key: response.key,
      amount: response.amount,
      order_id: response.order_id,
      email: response.email,
      handler: async (response) => {
        // POST /payments/verify with response
      },
    };
    new Razorpay(options).open();
    ```
    """
    try:
        # Create payment order
        transaction = await payment_service.create_order(
            db,
            current_user,
            request.plan_tier,
            request.billing_period,
            idempotency_key=request.idempotency_key,
        )

        # Get checkout payload
        payload = payment_service.get_order_creation_payload(
            transaction.amount_paise,
            transaction.razorpay_order_id,
            current_user.email,
        )

        await db.commit()

        return OrderCreateResponse(
            order_id=transaction.razorpay_order_id,
            key=payload["key"],
            amount=payload["amount"],
            email=payload["email"],
            currency="INR",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment order")


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    request: PaymentVerifyRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service),
) -> Any:
    """Verify and process a payment (called after client receives Razorpay response).

    Request body:
    {
      "order_id": "order_xyz...",
      "payment_id": "pay_xyz...",
      "signature": "signature_hex..."
    }

    This endpoint:
    1. Verifies the Razorpay signature (HMAC-SHA256)
    2. Marks the transaction as completed
    3. Activates the user's subscription
    """
    try:
        # Verify signature
        is_valid = payment_service.verify_payment_signature(
            request.order_id,
            request.payment_id,
            request.signature,
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid payment signature")

        # Find transaction
        transaction = await db.scalar(
            db.select(PaymentTransaction).where(
                PaymentTransaction.razorpay_order_id == request.order_id,
                PaymentTransaction.user_id == current_user.id,
            )
        )

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # If already completed, return success
        if transaction.status == PaymentStatus.completed:
            return PaymentVerifyResponse(
                ok=True,
                transaction_id=str(transaction.id),
                subscription_id=str(transaction.subscription_id) if transaction.subscription_id else None,
                status="completed",
                message="Payment already verified",
            )

        # Mark as completed (webhook will activate subscription)
        transaction.razorpay_payment_id = request.payment_id
        transaction.status = PaymentStatus.completed

        await db.commit()
        await db.refresh(transaction)

        return PaymentVerifyResponse(
            ok=True,
            transaction_id=str(transaction.id),
            subscription_id=str(transaction.subscription_id) if transaction.subscription_id else None,
            status="completed",
            message="Payment verified successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify payment")


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(
    request: Request,
    db: DbSession,
    payment_service: PaymentService = Depends(get_payment_service),
) -> Any:
    """Handle Razorpay webhooks (idempotent).

    Razorpay sends webhooks for:
    - payment.authorized: Payment successful
    - payment.failed: Payment failed

    Webhook body:
    {
      "event": "payment.authorized",
      "payload": {
        "payment": {
          "entity": {
            "id": "pay_xyz...",
            "order_id": "order_abc...",
            ...
          }
        }
      }
    }

    This endpoint is idempotent—rerunning with same data is safe.
    """
    try:
        # Get webhook payload
        body = await request.json()
        event_type = body.get("event", "")
        webhook_data = body

        logger.info(f"Received webhook event: {event_type}")

        # Process webhook (idempotent)
        transaction = await payment_service.process_webhook(
            db,
            webhook_data,
            event_type,
        )

        if transaction:
            await db.commit()
            logger.info(
                f"Webhook processed: {event_type} for transaction {transaction.id}"
            )

        return WebhookResponse(ok=True, message="Webhook processed")

    except ValueError as e:
        logger.error(f"Invalid webhook data: {e}")
        # Return 400 to signal Razorpay to retry (don't return 500 unless it's our fault)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process webhook")
