from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.dependencies import DbSession, get_current_user
from core.enum_utils import coerce_enum
from core.security import hash_password
from models import (
    Application,
    EmploymentType,
    JobPosting,
    JobStatus,
    JobType,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from services.user_service import create_user_with_profile
from services.admin_service import get_dashboard_stats
from services.subscription_service import log_subscription_change
from schemas import JobCreate, JobUpdate
router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


# ── Schemas ──────────────────────────────────────────────────────────────────


class AdminUserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: str
    name: Optional[str] = None
    plan_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: bool = True


class AdminSubOut(BaseModel):
    id: str
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    role: str
    plan_tier: str
    status: str
    started_at: str
    renews_at: Optional[str] = None


class AdminJobOut(BaseModel):
    id: str
    title: str
    company_name: Optional[str] = None
    company_id: str
    status: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    created_at: str
    application_count: int = 0
    department: Optional[str] = None
    job_role: Optional[str] = None
    job_level: Optional[str] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_unit: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    job_type: Optional[str] = None
    required_skills: Optional[list[str]] = None
    num_openings: Optional[int] = 1
    application_deadline: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None


class DashboardStats(BaseModel):
    total_users: int = 0
    total_candidates: int = 0
    total_companies: int = 0
    total_admins: int = 0
    total_jobs: int = 0
    active_jobs: int = 0
    total_applications: int = 0
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    plan_breakdown: dict = {}


class UserStatusUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Any) -> Optional[UserRole]:
        return coerce_enum(UserRole, v, "role")


class UserCreate(BaseModel):
    email: str
    password: str
    role: UserRole = UserRole.candidate
    is_active: bool = True

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Any) -> UserRole:
        res = coerce_enum(UserRole, v, "role")
        return res if res is not None else UserRole.candidate


class SubStatusUpdate(BaseModel):
    plan_tier: Optional[PlanTier] = None
    status: Optional[SubscriptionStatus] = None
    role: Optional[UserRole] = None

    @field_validator("plan_tier", mode="before")
    @classmethod
    def validate_plan_tier(cls, v: Any) -> Optional[PlanTier]:
        return coerce_enum(PlanTier, v, "plan_tier")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Optional[SubscriptionStatus]:
        return coerce_enum(SubscriptionStatus, v, "status")

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Any) -> Optional[UserRole]:
        return coerce_enum(UserRole, v, "role")


class SubCreate(BaseModel):
    user_id: str
    role: UserRole
    plan_tier: PlanTier
    status: SubscriptionStatus = SubscriptionStatus.pending  # Step 6A: Default to pending, not active

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Any) -> UserRole:
        return coerce_enum(UserRole, v, "role", allow_none=False)

    @field_validator("plan_tier", mode="before")
    @classmethod
    def validate_plan_tier(cls, v: Any) -> PlanTier:
        return coerce_enum(PlanTier, v, "plan_tier", allow_none=False)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> SubscriptionStatus:
        res = coerce_enum(SubscriptionStatus, v, "status")
        return res if res is not None else SubscriptionStatus.pending  # Default to pending


class SubscriptionGrant(BaseModel):
    """Step 6C: Manual admin grant of subscription (payment mode disabled only)."""
    user_id: str
    plan_tier: PlanTier
    reason: str  # Required: why admin is granting this
    started_at: Optional[datetime] = None  # Default: now
    ends_at: Optional[datetime] = None  # Default: 30 days from now

    @field_validator("plan_tier", mode="before")
    @classmethod
    def validate_plan_tier(cls, v: Any) -> PlanTier:
        return coerce_enum(PlanTier, v, "plan_tier", allow_none=False)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/me")
async def get_me(current_admin: User = Depends(get_current_admin)) -> Any:
    return {"status": "ok", "role": "admin"}


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats_route(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    stats = await get_dashboard_stats(db)
    return DashboardStats(**stats)


@router.get("/users", response_model=List[AdminUserOut])
async def get_all_users(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(User).options(
        selectinload(User.subscription),
        selectinload(User.company),
        selectinload(User.candidate_profile),
    )
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    if role:
        query = query.where(User.role == role)
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    out = []
    for u in users:
        name = None
        if u.company:
            name = u.company.name
        elif u.candidate_profile:
            # Try to get name from weblinks first
            if u.candidate_profile.weblinks:
                name = (
                    u.candidate_profile.weblinks.get('full_name') or
                    u.candidate_profile.weblinks.get('display_name') or
                    u.candidate_profile.weblinks.get('name')
                )
            # Fallback to parsing email if no name in weblinks
            if not name:
                name = (
                    u.email.split("@")[0]
                    .replace(".", " ")
                    .replace("_", " ")
                    .title()
                )
        plan_tier = None
        sub_status = None
        if u.subscription:
            plan_tier = str(
                u.subscription.plan_tier.value
                if hasattr(u.subscription.plan_tier, "value")
                else u.subscription.plan_tier
            )
            sub_status = str(
                u.subscription.status.value
                if hasattr(u.subscription.status, "value")
                else u.subscription.status
            )
        out.append(
            AdminUserOut(
                id=str(u.id),
                email=u.email,
                role=str(u.role.value if hasattr(u.role, "value") else u.role),
                created_at=u.created_at.isoformat(),
                name=name,
                plan_tier=plan_tier,
                subscription_status=sub_status,
            )
        )
    return out


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserStatusUpdate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if update_data.role is not None:
        user.role = coerce_enum(UserRole, update_data.role, "role", allow_none=False)
    if update_data.is_active is not None:
        user.is_active = update_data.is_active
    if update_data.email is not None:
        user.email = update_data.email
    await db.commit()
    await db.refresh(user)
    return {
        "ok": True,
        "id": str(user.id),
        "role": str(
            user.role.value if hasattr(user.role, "value") else user.role
        ),
    }


@router.post("/users")
async def create_user(
    create_data: UserCreate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    role = coerce_enum(UserRole, create_data.role, "role", allow_none=False)
    user = await create_user_with_profile(
        db=db,
        email=create_data.email,
        password=create_data.password,
        role=role,
        is_active=create_data.is_active,
    )
    await db.commit()
    await db.refresh(user)
    return {"ok": True, "id": str(user.id)}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    from services.account_deletion_service import delete_user_account

    deleted = await delete_user_account(db, UUID(user_id) if isinstance(user_id, str) else user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return {"ok": True}


@router.get("/subscriptions", response_model=List[AdminSubOut])
async def get_all_subscriptions(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
    status_filter: Optional[str] = Query(None, alias="status"),
    plan: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Subscription).options(
        selectinload(Subscription.user)
        .selectinload(User.company),
        selectinload(Subscription.user)
        .selectinload(User.candidate_profile)
    )
    if status_filter:
        query = query.where(Subscription.status == status_filter)
    if plan:
        query = query.where(Subscription.plan_tier == plan)
    query = (
        query.order_by(Subscription.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    subs = result.scalars().all()

    out = []
    for s in subs:
        user_email = s.user.email if s.user else None
        # Try to get a friendly name
        user_name = None
        if s.user:
            if s.user.company:
                user_name = s.user.company.name
            elif s.user.candidate_profile:
                # Try to get name from weblinks first
                if s.user.candidate_profile.weblinks:
                    user_name = (
                        s.user.candidate_profile.weblinks.get('full_name')
                        or s.user.candidate_profile.weblinks.get(
                            'display_name'
                        )
                        or s.user.candidate_profile.weblinks.get('name')
                    )
                # Fallback to parsing email if no name in weblinks
                if not user_name:
                    user_name = (
                        s.user.email.split("@")[0]
                        .replace(".", " ")
                        .replace("_", " ")
                        .title()
                    )
        out.append(
            AdminSubOut(
                id=str(s.id),
                user_id=str(s.user_id),
                user_email=user_email,
                user_name=user_name,
                role=str(s.role.value if hasattr(s.role, "value") else s.role),
                plan_tier=str(
                    s.plan_tier.value
                    if hasattr(s.plan_tier, "value")
                    else s.plan_tier
                ),
                status=str(
                    s.status.value if hasattr(s.status, "value") else s.status
                ),
                started_at=s.started_at.isoformat(),
                renews_at=s.renews_at.isoformat() if s.renews_at else None,
            )
        )
    return out


@router.patch("/subscriptions/{sub_id}")
async def update_subscription(
    sub_id: str,
    update_data: SubStatusUpdate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Step 6A: Update subscription with audit logging.
    
    Restrictions:
    - status can only be changed to 'active' if payment is verified (require reason with transaction ID)
    - Admins must provide reason for any status change to active
    """
    from services.subscription_service import log_subscription_change
    
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Track changes for audit log
    old_plan_tier = sub.plan_tier.value if sub.plan_tier else None
    old_status = sub.status.value if sub.status else None
    
    # If changing status to active, require explicit reason with payment proof
    if update_data.status is not None:
        new_status = coerce_enum(SubscriptionStatus, update_data.status, "status", allow_none=False)
        if new_status == SubscriptionStatus.active and old_status != "active":
            # Reject: must go through payment verification flow
            raise HTTPException(
                status_code=403,
                detail="Cannot manually activate subscription. Use payment gateway webhook instead.",
            )
        sub.status = new_status
    
    if update_data.plan_tier is not None:
        sub.plan_tier = coerce_enum(PlanTier, update_data.plan_tier, "plan_tier", allow_none=False)
    
    if update_data.role is not None:
        sub.role = coerce_enum(UserRole, update_data.role, "role", allow_none=False)
    
    await db.flush()
    
    # Log the change
    new_plan_tier = sub.plan_tier.value if sub.plan_tier else None
    new_status = sub.status.value if sub.status else None
    
    await log_subscription_change(
        db,
        subscription_id=sub.id,
        user_id=sub.user_id,
        admin_id=current_admin.id,
        action="update",
        old_plan_tier=old_plan_tier,
        new_plan_tier=new_plan_tier,
        old_status=old_status,
        new_status=new_status,
        reason="Admin override (manual update)",
    )
    
    await db.commit()
    await db.refresh(sub)
    return {"ok": True}


@router.post("/subscriptions")
async def create_subscription(
    create_data: SubCreate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Step 6A: Create subscription with audit logging.
    
    - Always creates with status=pending (default in SubCreate)
    - Must transition to active via payment gateway webhook only
    """
    sub = Subscription(
        user_id=UUID(create_data.user_id),
        role=coerce_enum(UserRole, create_data.role, "role", allow_none=False),
        plan_tier=coerce_enum(PlanTier, create_data.plan_tier, "plan_tier", allow_none=False),
        status=coerce_enum(SubscriptionStatus, create_data.status, "status", allow_none=False),
    )
    db.add(sub)
    await db.flush()
    
    # Log the creation
    await log_subscription_change(
        db,
        subscription_id=sub.id,
        user_id=UUID(create_data.user_id),
        admin_id=current_admin.id,
        action="create",
        new_plan_tier=sub.plan_tier.value,
        new_status=sub.status.value,
        reason="Admin creation",
    )
    
    await db.commit()
    await db.refresh(sub)
    return {"ok": True, "id": str(sub.id)}


@router.post("/subscriptions/grant")
async def grant_subscription(
    grant_data: SubscriptionGrant,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Step 6C: Admin grant of active subscription (manual override, payments disabled mode).
    
    This endpoint activates a subscription immediately without payment verification.
    Use cases:
    - Manual grants during disabled payment mode
    - Special promotions or trial grants
    - Administrative overrides
    
    The subscription is created with status=active and audit-logged with admin_id.
    """
    # Get user
    user = await db.get(User, grant_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate plan tier matches user role
    from services.subscription_service import validate_plan_tier
    plan_tier = await validate_plan_tier(grant_data.plan_tier.value, user.role)
    
    # Cancel any existing active subscriptions
    from services.subscription_service import cancel_active_subscriptions
    await cancel_active_subscriptions(db, user.id, admin_id=current_admin.id)
    
    # Set default dates
    started_at = grant_data.started_at or datetime.now(timezone.utc)
    ends_at = grant_data.ends_at or (started_at + timedelta(days=30))
    
    # Create active subscription directly (grant bypasses payment)
    sub = Subscription(
        user_id=user.id,
        role=user.role,
        plan_tier=plan_tier,
        status=SubscriptionStatus.active,  # Step 6C: Granted subscriptions are immediately active
        started_at=started_at,
        renews_at=ends_at,
    )
    db.add(sub)
    await db.flush()
    
    # Log the grant with admin_id
    await log_subscription_change(
        db,
        subscription_id=sub.id,
        user_id=user.id,
        admin_id=current_admin.id,
        action="grant",  # Special action type
        new_plan_tier=plan_tier.value,
        new_status=SubscriptionStatus.active.value,
        reason=grant_data.reason,  # Admin-provided reason
    )
    
    await db.commit()
    await db.refresh(sub)
    
    return {
        "ok": True,
        "id": str(sub.id),
        "user_id": str(sub.user_id),
        "plan_tier": sub.plan_tier.value,
        "status": sub.status.value,
        "started_at": sub.started_at.isoformat(),
        "renews_at": sub.renews_at.isoformat() if sub.renews_at else None,
    }


@router.delete("/subscriptions/{sub_id}")
async def delete_subscription(
    sub_id: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Step 6A: Soft-delete subscription (mark as cancelled).
    
    Hard deletion disabled for audit trail preservation.
    Use PATCH with status=cancelled for controlled cancellation.
    """
    raise HTTPException(
        status_code=405,
        detail="Hard delete not allowed. Use PATCH to set status=cancelled instead.",
    )


@router.get("/jobs", response_model=List[AdminJobOut])
async def get_all_jobs(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(JobPosting).options(selectinload(JobPosting.company))
    if search:
        query = query.where(JobPosting.title.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(JobPosting.status == status_filter)
    query = (
        query.order_by(JobPosting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    out = []
    for j in jobs:
        # Count applications
        app_count = (
            await db.scalar(
                select(func.count())
                .select_from(Application)
                .where(Application.job_id == j.id)
            )
            or 0
        )
        out.append(
            AdminJobOut(
                id=str(j.id),
                title=j.title,
                company_name=j.company.name if j.company else None,
                company_id=str(j.company_id),
                status=str(
                    j.status.value if hasattr(j.status, "value") else j.status
                ),
                location=j.location
                or ", ".join(filter(None, [j.city, j.state, j.country])),
                employment_type=j.employment_type,
                created_at=j.created_at.isoformat(),
                application_count=app_count,
                department=j.department,
                job_role=j.job_role,
                job_level=j.job_level,
                experience_range=j.experience_range,
                min_salary=j.min_salary,
                max_salary=j.max_salary,
                salary_unit=j.salary_unit,
                country=j.country,
                state=j.state,
                city=j.city,
                job_type=str(j.job_type.value) if hasattr(j.job_type, "value") else j.job_type,
                required_skills=j.required_skills,
                num_openings=j.num_openings,
                application_deadline=j.application_deadline.isoformat() if j.application_deadline else None,
                description=j.description,
                responsibilities=j.responsibilities,
                requirements=j.requirements,
                benefits=j.benefits,
            )
        )
    return out


@router.patch("/jobs/{job_id}")
@router.put("/jobs/{job_id}")
async def update_job_status(
    job_id: str,
    update_data: JobUpdate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if key == "status":
            job.status = coerce_enum(JobStatus, value, "status", allow_none=False)
        elif key == "job_type":
            job.job_type = coerce_enum(JobType, value, "job_type")
        elif key == "employment_type":
            emp = coerce_enum(EmploymentType, value, "employment_type")
            job.employment_type = emp.value if emp else None
        else:
            setattr(job, key, value)
        
    await db.commit()
    await db.refresh(job)
    return {"ok": True}


@router.post("/jobs")
async def create_job(
    create_data: JobCreate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    create_dict = create_data.model_dump(exclude_unset=True)
    if "status" in create_dict:
        create_dict["status"] = coerce_enum(JobStatus, create_dict["status"], "status", allow_none=False)
    if "job_type" in create_dict:
        create_dict["job_type"] = coerce_enum(JobType, create_dict["job_type"], "job_type")
    if "employment_type" in create_dict:
        emp = coerce_enum(EmploymentType, create_dict["employment_type"], "employment_type")
        create_dict["employment_type"] = emp.value if emp else None

    job = JobPosting(**create_dict)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"ok": True, "id": str(job.id)}


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()
    return {"ok": True}
