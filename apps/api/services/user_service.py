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
    raw = (plan or ("complete" if role == UserRole.candidate else "corporate_annual")).lower()
    if raw in ("free", "basic", "premium", "elite"):
        raw = "complete"
    elif raw in ("starter", "growth", "scale"):
        raw = "corporate_annual"
    try:
        return PlanTier(raw)
    except ValueError:
        return PlanTier.complete if role == UserRole.candidate else PlanTier.corporate_annual

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

    parsed_plan = parse_plan(plan, role)
    sub = Subscription(
        user_id=user.id,
        role=role,
        plan_tier=parsed_plan,
        status=SubscriptionStatus.active,
        renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)

    if role == UserRole.candidate:
        weblinks = {"display_name": name} if name else {}
        db.add(CandidateProfile(user_id=user.id, weblinks=weblinks))
    else:
        db.add(Company(user_id=user.id, name=name or "", industry=industry))

    await db.flush()
    return user
