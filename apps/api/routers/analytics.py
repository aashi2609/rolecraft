import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import require_role
from models import Application, ApplicationStatus, FitmentResult, JobPosting, SavedJob, User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


async def get_candidate_analytics(user: User, db: AsyncSession, days: int = 30):
    """Generate analytics data for candidates."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total applications
    total_applications = await db.scalar(
        select(func.count(Application.id)).where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date
        )
    )
    
    # Applications by status
    status_counts = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date
        )
        .group_by(Application.status)
    )
    status_distribution = {status.value: count for status, count in status_counts.all()}
    
    # Saved jobs count
    saved_jobs = await db.scalar(
        select(func.count(SavedJob.job_id)).where(SavedJob.candidate_id == user.id)
    )
    
    # Average fitment score
    avg_fitment = await db.scalar(
        select(func.avg(FitmentResult.score)).where(
            FitmentResult.candidate_id == user.id,
            FitmentResult.computed_at >= cutoff_date
        )
    )
    
    # Application trend (grouped by day)
    application_trend = await db.execute(
        select(
            func.date(Application.applied_at).label('date'),
            func.count(Application.id).label('count')
        )
        .where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date
        )
        .group_by(func.date(Application.applied_at))
        .order_by(func.date(Application.applied_at))
    )
    trend_data = [{"date": str(date), "count": count} for date, count in application_trend.all()]
    
    return {
        "period_days": days,
        "total_applications": total_applications or 0,
        "saved_jobs": saved_jobs or 0,
        "average_fitment_score": round(avg_fitment or 0, 2),
        "status_distribution": status_distribution,
        "application_trend": trend_data,
    }


async def get_company_analytics(user: User, db: AsyncSession, days: int = 30):
    """Generate analytics data for companies."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all company jobs
    jobs = await db.execute(
        select(JobPosting)
        .where(JobPosting.company_id == user.id)
    )
    job_ids = [job.id for job in jobs.scalars().all()]
    
    if not job_ids:
        return {
            "period_days": days,
            "total_jobs": 0,
            "total_applications": 0,
            "average_fitment_score": 0,
            "status_distribution": {},
            "response_rate": 0,
            "application_trend": [],
        }
    
    # Total applications
    total_applications = await db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date
        )
    )
    
    # Applications by status
    status_counts = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date
        )
        .group_by(Application.status)
    )
    status_distribution = {status.value: count for status, count in status_counts.all()}
    
    # Average fitment score
    avg_fitment = await db.scalar(
        select(func.avg(FitmentResult.score)).where(
            FitmentResult.job_id.in_(job_ids),
            FitmentResult.computed_at >= cutoff_date
        )
    )
    
    # Response rate (applications that moved beyond 'applied')
    responded_count = await db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date,
            Application.status != ApplicationStatus.applied
        )
    )
    response_rate = (responded_count / total_applications * 100) if total_applications else 0
    
    # Application trend (grouped by day)
    application_trend = await db.execute(
        select(
            func.date(Application.applied_at).label('date'),
            func.count(Application.id).label('count')
        )
        .where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date
        )
        .group_by(func.date(Application.applied_at))
        .order_by(func.date(Application.applied_at))
    )
    trend_data = [{"date": str(date), "count": count} for date, count in application_trend.all()]
    
    return {
        "period_days": days,
        "total_jobs": len(job_ids),
        "total_applications": total_applications or 0,
        "average_fitment_score": round(avg_fitment or 0, 2),
        "status_distribution": status_distribution,
        "response_rate": round(response_rate, 2),
        "application_trend": trend_data,
    }


@router.get("/analytics/candidate")
async def candidate_analytics(
    days: int = 30,
    user: User = Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for the current candidate."""
    if days < 1 or days > 365:
        days = 30
    
    return await get_candidate_analytics(user, db, days)


@router.get("/analytics/company")
async def company_analytics(
    days: int = 30,
    user: User = Depends(require_role(UserRole.company)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for the current company."""
    if days < 1 or days > 365:
        days = 30
    
    return await get_company_analytics(user, db, days)
