from typing import Annotated, Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.security import decode_access_token
from models import (
    JobPosting,
    JobStatus,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        return None

    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def require_role(*roles: UserRole) -> Callable:
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
            )
        return user

    return _checker


async def get_user_plan(user: User, db: AsyncSession) -> PlanTier:
    if user.subscription and user.subscription.status == SubscriptionStatus.active:
        return user.subscription.plan_tier
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.active,
        )
        .order_by(Subscription.started_at.desc())
    )
    sub = result.scalar_one_or_none()
    if sub:
        return sub.plan_tier
    return PlanTier.complete if user.role == UserRole.candidate else PlanTier.corporate_annual


async def check_plan_limit(
    user: User, db: AsyncSession, resource: str, extra: int = 1
) -> None:
    """Validate feature category permissions based on user's active plan."""
    if user.subscription and user.subscription.status != SubscriptionStatus.active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="An active subscription is required to access RoleCraft services — please choose a plan to activate your account.",
        )

    plan = await get_user_plan(user, db)

    # Resume creation/generation gating
    if resource in ("resume_generation", "resume_verticals"):
        if plan not in (PlanTier.resume_builder, PlanTier.complete):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your plan doesn't include resume generation — upgrade to Resume Builder or Complete",
            )

    # Job search & application gating
    elif resource in ("job_search", "applications", "messages"):
        if user.role == UserRole.candidate and plan not in (PlanTier.job_search, PlanTier.complete):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your plan doesn't include job search & applications — upgrade to Job Search or Complete",
            )

    # Corporate job postings gating
    elif resource in ("job_postings", "candidate_search"):
        if user.role == UserRole.company and plan not in (PlanTier.corporate_annual, PlanTier.corporate_lifetime):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your plan doesn't include corporate job posting and candidate search — please subscribe to a Corporate plan.",
            )


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
CandidateUser = Annotated[User, Depends(require_role(UserRole.candidate))]
CompanyUser = Annotated[User, Depends(require_role(UserRole.company))]
