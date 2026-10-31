"""Subscription management service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from models import (
    PlanTier,
    Subscription,
    SubscriptionStatus,
    SubscriptionAuditLog,
    UserRole,
)
from schemas import SubscriptionCreate, SubscriptionOut


async def log_subscription_change(
    db,
    subscription_id: UUID,
    user_id: UUID,
    action: str,
    admin_id: Optional[UUID] = None,
    old_plan_tier: Optional[str] = None,
    new_plan_tier: Optional[str] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    reason: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
) -> None:
    """Log a subscription change for audit trail."""
    audit = SubscriptionAuditLog(
        subscription_id=subscription_id,
        user_id=user_id,
        admin_id=admin_id,
        action=action,
        old_plan_tier=old_plan_tier,
        new_plan_tier=new_plan_tier,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        payment_transaction_id=payment_transaction_id,
    )
    db.add(audit)


async def get_active_subscription(db, user_id: UUID) -> Optional[Subscription]:
    """Get the active subscription for a user."""
    return await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.active,
        )
        .order_by(Subscription.started_at.desc())
    )


async def validate_plan_tier(tier_str: str, user_role: UserRole) -> PlanTier:
    """Validate and convert plan tier string to enum, checking role compatibility."""
    try:
        tier = PlanTier(tier_str.lower())
    except ValueError as exc:
        raise ValueError("Invalid plan_tier") from exc

    # Validate plan tier matches user role
    if user_role == UserRole.candidate and tier not in [
        PlanTier.resume_builder,
        PlanTier.job_search,
        PlanTier.complete,
    ]:
        raise ValueError("Invalid plan tier for candidate role")
    if user_role == UserRole.company and tier not in [
        PlanTier.corporate_annual,
        PlanTier.corporate_lifetime,
    ]:
        raise ValueError("Invalid plan tier for company role")

    return tier


async def cancel_active_subscriptions(db, user_id: UUID, admin_id: Optional[UUID] = None) -> None:
    """Cancel all active subscriptions for a user."""
    existing = (
        (
            await db.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.active,
                )
            )
        )
        .scalars()
        .all()
    )
    for s in existing:
        old_status = s.status.value
        s.status = SubscriptionStatus.cancelled
        # Log the cancellation
        await log_subscription_change(
            db,
            subscription_id=s.id,
            user_id=user_id,
            admin_id=admin_id,
            action="cancel",
            old_status=old_status,
            new_status=SubscriptionStatus.cancelled.value,
            reason="Replaced by new subscription",
        )


async def create_subscription(
    db,
    user_id: UUID,
    user_role: UserRole,
    tier: PlanTier,
    admin_id: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> Subscription:
    """Create a new subscription for a user."""
    sub = Subscription(
        user_id=user_id,
        role=user_role,
        plan_tier=tier,
        status=SubscriptionStatus.pending,  # Step 6A: Always start as pending
        renews_at=None,  # No renewal until payment verified
    )
    db.add(sub)
    await db.flush()
    
    # Log the creation
    await log_subscription_change(
        db,
        subscription_id=sub.id,
        user_id=user_id,
        admin_id=admin_id,
        action="create",
        new_plan_tier=tier.value,
        new_status=SubscriptionStatus.pending.value,
        reason=reason or "User registration",
    )
    
    await db.refresh(sub)
    return sub


async def upsert_subscription(
    db,
    body: SubscriptionCreate,
    user_id: UUID,
    user_role: UserRole,
    admin_id: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> SubscriptionOut:
    """Create or update a subscription for a user.

    Cancels existing active subscriptions and creates a new one.
    """
    # Validate and convert plan tier
    tier = await validate_plan_tier(body.plan_tier, user_role)

    # Cancel existing active subscriptions
    await cancel_active_subscriptions(db, user_id, admin_id=admin_id)

    # Create new subscription
    sub = await create_subscription(
        db,
        user_id,
        user_role,
        tier,
        admin_id=admin_id,
        reason=reason,
    )

    return SubscriptionOut.model_validate(sub)
