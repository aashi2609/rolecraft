import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import require_role
from models import User, UserRole
from schemas import CandidateAnalyticsOut, CompanyAnalyticsOut
from services.analytics_service import get_candidate_analytics, get_company_analytics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/candidate", response_model=CandidateAnalyticsOut)
async def candidate_analytics(
    days: int = 30,
    user: User = Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for the current candidate."""
    if days < 1 or days > 365:
        days = 30

    return await get_candidate_analytics(user, db, days)


@router.get("/analytics/company", response_model=CompanyAnalyticsOut)
async def company_analytics(
    days: int = 30,
    user: User = Depends(require_role(UserRole.company)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for the current company."""
    if days < 1 or days > 365:
        days = 30

    return await get_company_analytics(user, db, days)
