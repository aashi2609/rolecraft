from typing import Annotated, Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.security import decode_access_token
from models import JobPosting, JobStatus, PlanTier, Subscription, SubscriptionStatus, User, UserRole

security = HTTPBearer(auto_error=False)

FREE_CANDIDATE_PLANS = {PlanTier.free, PlanTier.basic}
FREE_COMPANY_PLANS = {PlanTier.starter, PlanTier.free, PlanTier.basic}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _checker


async def get_user_plan(user: User, db: AsyncSession) -> PlanTier:
    if user.subscription and user.subscription.status == SubscriptionStatus.active:
        return user.subscription.plan_tier
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active)
        .order_by(Subscription.started_at.desc())
    )
    sub = result.scalar_one_or_none()
    if sub:
        return sub.plan_tier
    return PlanTier.basic if user.role == UserRole.candidate else PlanTier.starter


async def check_plan_limit(user: User, db: AsyncSession, resource: str, extra: int = 1) -> None:
    """Raise 402/403 when free-tier caps are exceeded."""
    plan = await get_user_plan(user, db)

    if resource == "resume_verticals":
        if plan in FREE_CANDIDATE_PLANS and extra > 1:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Free plan allows 1 target role at a time. Upgrade to generate more.",
            )
        from models import Resume

        count = await db.scalar(
            select(func.count()).select_from(Resume).where(Resume.candidate_id == user.id)
        )
        if plan in FREE_CANDIDATE_PLANS and (count or 0) >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You've reached your plan's resume generation limit — upgrade to generate more.",
            )

    if resource == "job_postings":
        if plan not in FREE_COMPANY_PLANS:
            return
        count = await db.scalar(
            select(func.count())
            .select_from(JobPosting)
            .where(
                JobPosting.company_id == user.id,
                JobPosting.status.in_([JobStatus.live, JobStatus.draft]),
            )
        )
        if (count or 0) >= 2:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Free plan allows up to 2 active job postings. Upgrade for unlimited.",
            )


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
CandidateUser = Annotated[User, Depends(require_role(UserRole.candidate))]
CompanyUser = Annotated[User, Depends(require_role(UserRole.company))]
