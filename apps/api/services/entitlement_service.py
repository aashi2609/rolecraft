"""Step 6B: Entitlement service - single source of truth for plan features.

All feature access gated through this service.
No hardcoded limits, no scattered checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, NamedTuple
from uuid import UUID

from sqlalchemy import and_, select

from models import Subscription, SubscriptionStatus, User, UserRole, PlanTier


class PlanFeatures(NamedTuple):
    """Features and quotas for a plan."""
    plan_tier: Optional[PlanTier]
    status: str  # active, pending, cancelled
    is_active: bool
    valid_until: Optional[datetime]
    
    # Candidate plan features
    resume_generation: int  # Unlimited = 9999
    resume_tailoring: int  # Per application
    ats_score_checks: int
    pdf_downloads: int
    target_roles: int  # Concurrent roles to optimize for
    
    # Job search features
    job_search: bool
    job_applications_per_day: int
    saved_jobs: int
    candidate_messaging: bool
    
    # Company plan features
    job_postings: int
    active_jobs_concurrent: int
    candidate_search: bool
    candidate_messaging: bool
    candidate_profiles_viewable: int


# ── PLAN FEATURES MASTER TABLE ────────────────────────────────────────────────

PLAN_FEATURES: dict[str, PlanFeatures] = {
    # Free tier (pending subscription)
    "free": PlanFeatures(
        plan_tier=None,
        status="pending",
        is_active=False,
        valid_until=None,
        resume_generation=0,
        resume_tailoring=0,
        ats_score_checks=0,
        pdf_downloads=0,
        target_roles=0,
        job_search=False,
        job_applications_per_day=0,
        saved_jobs=0,
        candidate_messaging=False,
        job_postings=0,
        active_jobs_concurrent=0,
        candidate_search=False,
        candidate_messaging=False,
        candidate_profiles_viewable=0,
    ),
    
    # Candidate plans
    "resume_builder": PlanFeatures(
        plan_tier=PlanTier.resume_builder,
        status="active",
        is_active=True,
        valid_until=None,  # Determined at runtime
        resume_generation=9999,  # Unlimited
        resume_tailoring=9999,  # Unlimited
        ats_score_checks=9999,  # Unlimited
        pdf_downloads=9999,  # Unlimited
        target_roles=3,  # Up to 3 concurrent roles
        job_search=False,  # No job search
        job_applications_per_day=0,
        saved_jobs=0,
        candidate_messaging=False,
        job_postings=0,
        active_jobs_concurrent=0,
        candidate_search=False,
        candidate_messaging=False,
        candidate_profiles_viewable=0,
    ),
    
    "job_search": PlanFeatures(
        plan_tier=PlanTier.job_search,
        status="active",
        is_active=True,
        valid_until=None,
        resume_generation=0,  # No resume generation
        resume_tailoring=0,
        ats_score_checks=0,
        pdf_downloads=0,
        target_roles=0,
        job_search=True,
        job_applications_per_day=5,  # 5 per day
        saved_jobs=9999,  # Unlimited
        candidate_messaging=True,
        job_postings=0,
        active_jobs_concurrent=0,
        candidate_search=False,
        candidate_messaging=False,
        candidate_profiles_viewable=0,
    ),
    
    "complete": PlanFeatures(
        plan_tier=PlanTier.complete,
        status="active",
        is_active=True,
        valid_until=None,
        resume_generation=9999,  # Unlimited
        resume_tailoring=9999,  # Unlimited - tailored per application
        ats_score_checks=9999,  # Unlimited
        pdf_downloads=9999,  # Unlimited
        target_roles=9999,  # Unlimited roles
        job_search=True,
        job_applications_per_day=9999,  # Unlimited
        saved_jobs=9999,  # Unlimited
        candidate_messaging=True,
        job_postings=0,
        active_jobs_concurrent=0,
        candidate_search=False,
        candidate_messaging=False,
        candidate_profiles_viewable=0,
    ),
    
    # Company plans
    "corporate_annual": PlanFeatures(
        plan_tier=PlanTier.corporate_annual,
        status="active",
        is_active=True,
        valid_until=None,
        resume_generation=0,
        resume_tailoring=0,
        ats_score_checks=0,
        pdf_downloads=0,
        target_roles=0,
        job_search=False,
        job_applications_per_day=0,
        saved_jobs=0,
        candidate_messaging=False,
        job_postings=9999,  # Unlimited
        active_jobs_concurrent=10,  # 10 concurrent postings
        candidate_search=True,
        candidate_messaging=True,
        candidate_profiles_viewable=9999,  # Unlimited view depth
    ),
    
    "corporate_lifetime": PlanFeatures(
        plan_tier=PlanTier.corporate_lifetime,
        status="active",
        is_active=True,
        valid_until=None,  # No expiry
        resume_generation=0,
        resume_tailoring=0,
        ats_score_checks=0,
        pdf_downloads=0,
        target_roles=0,
        job_search=False,
        job_applications_per_day=0,
        saved_jobs=0,
        candidate_messaging=False,
        job_postings=9999,  # Unlimited
        active_jobs_concurrent=9999,  # Unlimited concurrent
        candidate_search=True,
        candidate_messaging=True,
        candidate_profiles_viewable=9999,  # Unlimited
    ),
}


async def get_entitlements(user: User, db) -> PlanFeatures:
    """
    Get entitlements for a user - single source of truth.
    
    Returns:
        PlanFeatures object with all feature flags and quotas
    
    Logic:
    - If no subscription or status != active → return free tier
    - If subscription expired (renews_at < now) → return free tier
    - Otherwise return plan features for plan_tier
    """
    if not user:
        return PLAN_FEATURES["free"]
    
    # Get active subscription (if any)
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.active,
        )
    )
    
    if not sub:
        return PLAN_FEATURES["free"]
    
    # Check expiry (if renews_at is past, subscription is expired)
    now = datetime.now(timezone.utc)
    if sub.renews_at and sub.renews_at < now:
        # Expired; would normally mark as cancelled via background job
        return PLAN_FEATURES["free"]
    
    # Return features for this plan
    plan_key = sub.plan_tier.value
    features = PLAN_FEATURES.get(plan_key, PLAN_FEATURES["free"])
    
    # Adjust valid_until based on subscription
    if sub.renews_at:
        return features._replace(valid_until=sub.renews_at)
    elif sub.plan_tier == PlanTier.corporate_lifetime:
        # No expiry for lifetime
        return features._replace(valid_until=None)
    else:
        # Active but no renews_at? Shouldn't happen, but assume 30 days
        return features._replace(valid_until=None)


class EntitlementError(Exception):
    """Raised when user lacks entitlement for a feature."""
    def __init__(self, code: str, message: str, plan_required: Optional[str] = None):
        self.code = code  # plan_required, quota_exceeded, plan_expired
        self.message = message
        self.plan_required = plan_required  # If plan_required, which plan to suggest
        super().__init__(message)


async def require_feature(
    user: User,
    db,
    feature: str,  # resume_generation, candidate_search, job_applications, etc.
) -> None:
    """
    Check if user has access to a feature.
    
    Raises:
        EntitlementError with code='plan_required' if feature not in plan
    """
    entitlements = await get_entitlements(user, db)
    
    # Feature mapping to entitlements
    feature_checks = {
        "resume_generation": entitlements.resume_generation > 0,
        "candidate_search": entitlements.candidate_search,
        "job_applications": entitlements.job_applications_per_day > 0,
        "job_posting": entitlements.job_postings > 0,
        "job_search": entitlements.job_search,
        "messaging": entitlements.candidate_messaging,
        "ats_score": entitlements.ats_score_checks > 0,
    }
    
    if feature not in feature_checks:
        raise ValueError(f"Unknown feature: {feature}")
    
    if not feature_checks[feature]:
        # Suggest appropriate plan
        if user.role == UserRole.candidate:
            suggestion = "complete"  # Full access plan for candidates
        else:
            suggestion = "corporate_annual"  # Standard company plan
        
        raise EntitlementError(
            code="plan_required",
            message=f"Feature '{feature}' requires a paid plan",
            plan_required=suggestion,
        )


async def require_quota(
    user: User,
    db,
    quota_name: str,  # resume_count, active_jobs, etc.
    current_usage: int,
) -> None:
    """
    Check if user has quota remaining for an action.
    
    Raises:
        EntitlementError with code='quota_exceeded' if limit reached
    """
    entitlements = await get_entitlements(user, db)
    
    quota_map = {
        "resume_generation": entitlements.resume_generation,
        "resume_tailoring": entitlements.resume_tailoring,
        "ats_score_checks": entitlements.ats_score_checks,
        "pdf_downloads": entitlements.pdf_downloads,
        "target_roles": entitlements.target_roles,
        "job_applications_per_day": entitlements.job_applications_per_day,
        "saved_jobs": entitlements.saved_jobs,
        "job_postings": entitlements.job_postings,
        "active_jobs_concurrent": entitlements.active_jobs_concurrent,
        "candidate_profiles_viewable": entitlements.candidate_profiles_viewable,
    }
    
    if quota_name not in quota_map:
        raise ValueError(f"Unknown quota: {quota_name}")
    
    limit = quota_map[quota_name]
    
    # 9999 means unlimited
    if limit >= 9999:
        return
    
    if current_usage >= limit:
        raise EntitlementError(
            code="quota_exceeded",
            message=f"Quota '{quota_name}' exceeded (limit: {limit})",
        )


async def check_plan_expired(user: User, db) -> bool:
    """Check if user's subscription has expired."""
    entitlements = await get_entitlements(user, db)
    
    if not entitlements.is_active:
        return True
    
    if entitlements.valid_until and entitlements.valid_until < datetime.now(timezone.utc):
        return True
    
    return False
