"""Subscription management service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from models import Subscription, UserRole, PlanTier, SubscriptionStatus
from schemas import SubscriptionOut, SubscriptionCreate


async def get_active_subscription(db, user_id: UUID) -> Optional[Subscription]:
    """Get the active subscription for a user."""
    return await db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.active)
        .order_by(Subscription.started_at.desc())
    )


async def validate_plan_tier(tier_str: str, user_role: UserRole) -> PlanTier:
    """Validate and convert plan tier string to enum, checking role compatibility."""
    try:
        tier = PlanTier(tier_str.lower())
    except ValueError as exc:
        raise ValueError("Invalid plan_tier") from exc

    # Validate plan tier matches user role
    if user_role == UserRole.candidate and tier not in [PlanTier.free, PlanTier.basic, PlanTier.premium, PlanTier.elite]:
        raise ValueError("Invalid plan tier for candidate role")
    if user_role == UserRole.company and tier not in [PlanTier.starter, PlanTier.growth, PlanTier.scale]:
        raise ValueError("Invalid plan tier for company role")
    
    return tier


async def cancel_active_subscriptions(db, user_id: UUID) -> None:
    """Cancel all active subscriptions for a user."""
    existing = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.active
            )
        )
    ).scalars().all()
    for s in existing:
        s.status = SubscriptionStatus.cancelled


async def create_subscription(
    db,
    user_id: UUID,
    user_role: UserRole,
    tier: PlanTier,
) -> Subscription:
    """Create a new subscription for a user."""
    sub = Subscription(
        user_id=user_id,
        role=user_role,
        plan_tier=tier,
        status=SubscriptionStatus.active,
        renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def upsert_subscription(
    db,
    body: SubscriptionCreate,
    user_id: UUID,
    user_role: UserRole,
) -> SubscriptionOut:
    """Create or update a subscription for a user.
    
    Cancels existing active subscriptions and creates a new one.
    """
    # Validate and convert plan tier
    tier = await validate_plan_tier(body.plan_tier, user_role)

    # Cancel existing active subscriptions
    await cancel_active_subscriptions(db, user_id)

    # Create new subscription
    sub = await create_subscription(db, user_id, user_role, tier)
    
    return SubscriptionOut.model_validate(sub)
