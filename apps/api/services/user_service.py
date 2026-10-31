from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import hash_password
from models import (
    User,
    UserRole,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    CandidateProfile,
    Company,
)

def parse_plan(plan: str | None, role: UserRole) -> PlanTier:
    default_tier = PlanTier.free if role == UserRole.candidate else PlanTier.corporate_annual
    if not plan:
        return default_tier
    raw = plan.strip().lower()
    try:
        return PlanTier(raw)
    except ValueError:
        return default_tier

async def create_user_with_profile(
    db: AsyncSession,
    email: str,
    password: str,
    role: UserRole,
    name: str | None = None,
    industry: str | None = None,
    plan: str | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()

    # Step 6A: Fix - Signup creates subscription with status=pending (not active)
    # Payment verification required before status=active is set
    parsed_plan = parse_plan(plan, role)
    sub = Subscription(
        user_id=user.id,
        role=role,
        plan_tier=parsed_plan,
        status=SubscriptionStatus.pending,  # Changed from active to pending
        renews_at=None,  # No renewal until payment verified
    )
    db.add(sub)

    if role == UserRole.candidate:
        weblinks = {"display_name": name} if name else {}
        db.add(CandidateProfile(user_id=user.id, weblinks=weblinks))
    else:
        db.add(Company(user_id=user.id, name=name or "", industry=industry))

    await db.flush()
    return user
