from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.dependencies import DbSession, get_current_user
from core.security import hash_password
from models import (
    Application,
    JobPosting,
    Subscription,
    User,
    UserRole,
)
from services.admin_service import get_dashboard_stats

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
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "candidate"
    is_active: bool = True


class SubStatusUpdate(BaseModel):
    plan_tier: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None


class SubCreate(BaseModel):
    user_id: str
    role: str
    plan_tier: str
    status: str = "active"


class JobAdminUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None


class JobCreate(BaseModel):
    company_id: str
    title: str
    status: str = "draft"
    location: Optional[str] = None
    employment_type: Optional[str] = None


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
        elif u.candidate_profile and u.candidate_profile.career_level:
            name = u.email.split("@")[0].replace(".", " ").title()
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
        user.role = update_data.role
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
    hashed_pwd = hash_password(create_data.password)
    user = User(
        email=create_data.email,
        password_hash=hashed_pwd,
        role=create_data.role,
        is_active=create_data.is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"ok": True, "id": str(user.id)}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
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
        selectinload(Subscription.user).selectinload(User.company)
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
        if s.user and s.user.company:
            user_name = s.user.company.name
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
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if update_data.plan_tier is not None:
        sub.plan_tier = update_data.plan_tier
    if update_data.status is not None:
        sub.status = update_data.status
    if update_data.role is not None:
        sub.role = update_data.role
    await db.commit()
    await db.refresh(sub)
    return {"ok": True}


@router.post("/subscriptions")
async def create_subscription(
    create_data: SubCreate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    sub = Subscription(
        user_id=create_data.user_id,
        role=create_data.role,
        plan_tier=create_data.plan_tier,
        status=create_data.status,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"ok": True, "id": str(sub.id)}


@router.delete("/subscriptions/{sub_id}")
async def delete_subscription(
    sub_id: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(sub)
    await db.commit()
    return {"ok": True}


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
            )
        )
    return out


@router.patch("/jobs/{job_id}")
async def update_job_status(
    job_id: str,
    update_data: JobAdminUpdate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if update_data.title is not None:
        job.title = update_data.title
    if update_data.status is not None:
        job.status = update_data.status
    if update_data.location is not None:
        job.location = update_data.location
    if update_data.employment_type is not None:
        job.employment_type = update_data.employment_type
    await db.commit()
    await db.refresh(job)
    return {"ok": True}


@router.post("/jobs")
async def create_job(
    create_data: JobCreate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
) -> Any:
    job = JobPosting(
        company_id=create_data.company_id,
        title=create_data.title,
        status=create_data.status,
        location=create_data.location,
        employment_type=create_data.employment_type,
    )
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
