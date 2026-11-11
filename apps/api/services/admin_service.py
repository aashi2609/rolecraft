"""Admin dashboard service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from models import (
    Application,
    JobPosting,
    JobStatus,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)


async def get_dashboard_stats(db) -> dict[str, Any]:
    """Get dashboard statistics for admin view.

    Returns counts for users, jobs, applications, subscriptions, and plan breakdown.
    """
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_candidates = (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.candidate)
        )
        or 0
    )
    total_companies = (
        await db.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.company)
        )
        or 0
    )
    total_admins = (
        await db.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.admin)
        )
        or 0
    )
    total_jobs = await db.scalar(select(func.count()).select_from(JobPosting)) or 0
    active_jobs = (
        await db.scalar(
            select(func.count())
            .select_from(JobPosting)
            .where(JobPosting.status == JobStatus.live)
        )
        or 0
    )
    total_applications = (
        await db.scalar(select(func.count()).select_from(Application)) or 0
    )
    total_subscriptions = (
        await db.scalar(select(func.count()).select_from(Subscription)) or 0
    )
    active_subscriptions = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.active)
        )
        or 0
    )

    # Plan breakdown
    plan_rows = await db.execute(
        select(Subscription.plan_tier, func.count())
        .where(Subscription.status == SubscriptionStatus.active)
        .group_by(Subscription.plan_tier)
    )
    plan_breakdown = {
        str(row[0].value if hasattr(row[0], "value") else row[0]): row[1]
        for row in plan_rows.all()
    }

    return {
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_companies": total_companies,
        "total_admins": total_admins,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
        "plan_breakdown": plan_breakdown,
    }
