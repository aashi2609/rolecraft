"""Analytics aggregation with short-lived in-memory cache."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Application,
    ApplicationStatus,
    FitmentResult,
    JobPosting,
    SavedJob,
    User,
)

_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(user_id: UUID, role: str, days: int) -> str:
    return f"{role}:{user_id}:{days}"


def _get_cached(user_id: UUID, role: str, days: int) -> dict[str, Any] | None:
    key = _cache_key(user_id, role, days)
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return payload


def _set_cached(user_id: UUID, role: str, days: int, payload: dict[str, Any]) -> None:
    key = _cache_key(user_id, role, days)
    _cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, payload)


async def get_candidate_analytics(
    user: User, db: AsyncSession, days: int = 30
) -> dict[str, Any]:
    cached = _get_cached(user.id, "candidate", days)
    if cached is not None:
        return cached

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    total_applications = await db.scalar(
        select(func.count(Application.id)).where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date,
        )
    )

    status_counts = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date,
        )
        .group_by(Application.status)
    )
    status_distribution = {status.value: count for status, count in status_counts.all()}

    saved_jobs = await db.scalar(
        select(func.count(SavedJob.job_id)).where(SavedJob.candidate_id == user.id)
    )

    avg_fitment = await db.scalar(
        select(func.avg(FitmentResult.score)).where(
            FitmentResult.candidate_id == user.id,
            FitmentResult.computed_at >= cutoff_date,
        )
    )

    application_trend = await db.execute(
        select(
            func.date(Application.applied_at).label("date"),
            func.count(Application.id).label("count"),
        )
        .where(
            Application.candidate_id == user.id,
            Application.applied_at >= cutoff_date,
        )
        .group_by(func.date(Application.applied_at))
        .order_by(func.date(Application.applied_at))
    )
    trend_data = [
        {"date": str(date), "count": count} for date, count in application_trend.all()
    ]

    payload = {
        "period_days": days,
        "total_applications": total_applications or 0,
        "saved_jobs": saved_jobs or 0,
        "average_fitment_score": round(float(avg_fitment or 0), 2),
        "status_distribution": status_distribution,
        "application_trend": trend_data,
    }
    _set_cached(user.id, "candidate", days, payload)
    return payload


async def get_company_analytics(
    user: User, db: AsyncSession, days: int = 30
) -> dict[str, Any]:
    cached = _get_cached(user.id, "company", days)
    if cached is not None:
        return cached

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    jobs = await db.execute(select(JobPosting).where(JobPosting.company_id == user.id))
    job_ids = [job.id for job in jobs.scalars().all()]

    if not job_ids:
        payload = {
            "period_days": days,
            "total_jobs": 0,
            "total_applications": 0,
            "average_fitment_score": 0.0,
            "status_distribution": {},
            "response_rate": 0.0,
            "application_trend": [],
        }
        _set_cached(user.id, "company", days, payload)
        return payload

    total_applications = await db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date,
        )
    )

    status_counts = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date,
        )
        .group_by(Application.status)
    )
    status_distribution = {status.value: count for status, count in status_counts.all()}

    avg_fitment = await db.scalar(
        select(func.avg(FitmentResult.score)).where(
            FitmentResult.job_id.in_(job_ids),
            FitmentResult.computed_at >= cutoff_date,
        )
    )

    responded_count = await db.scalar(
        select(func.count(Application.id)).where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date,
            Application.status != ApplicationStatus.applied,
        )
    )
    response_rate = (
        (responded_count / total_applications * 100) if total_applications else 0
    )

    application_trend = await db.execute(
        select(
            func.date(Application.applied_at).label("date"),
            func.count(Application.id).label("count"),
        )
        .where(
            Application.job_id.in_(job_ids),
            Application.applied_at >= cutoff_date,
        )
        .group_by(func.date(Application.applied_at))
        .order_by(func.date(Application.applied_at))
    )
    trend_data = [
        {"date": str(date), "count": count} for date, count in application_trend.all()
    ]

    payload = {
        "period_days": days,
        "total_jobs": len(job_ids),
        "total_applications": total_applications or 0,
        "average_fitment_score": round(float(avg_fitment or 0), 2),
        "status_distribution": status_distribution,
        "response_rate": round(float(response_rate), 2),
        "application_trend": trend_data,
    }
    _set_cached(user.id, "company", days, payload)
    return payload
