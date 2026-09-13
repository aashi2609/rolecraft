from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CurrentUser, DbSession
from core.security import create_access_token, hash_password, verify_password
from models import (
    CandidateProfile,
    Company,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)
from schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    SigninRequest,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _parse_plan(plan: str | None, role: UserRole) -> PlanTier:
    raw = (plan or ("complete" if role == UserRole.candidate else "corporate_annual")).lower()
    if raw in ("free", "basic", "premium", "elite"):
        raw = "complete"
    elif raw in ("starter", "growth", "scale"):
        raw = "corporate_annual"
    try:
        return PlanTier(raw)
    except ValueError:
        return PlanTier.complete if role == UserRole.candidate else PlanTier.corporate_annual


@router.post("/signup", response_model=TokenResponse)
async def signup(body: SignupRequest, db: DbSession):
    # Password complexity + role Literal already enforced by SignupRequest
    role = UserRole(body.role)
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email.lower(), password_hash=hash_password(body.password), role=role
    )
    db.add(user)
    await db.flush()

    plan = _parse_plan(body.plan, role)
    sub = Subscription(
        user_id=user.id,
        role=role,
        plan_tier=plan,
        status=SubscriptionStatus.active,
        renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)

    if role == UserRole.candidate:
        weblinks = {"display_name": body.name} if body.name else {}
        db.add(CandidateProfile(user_id=user.id, weblinks=weblinks))
    else:
        db.add(Company(user_id=user.id, name=body.name or "", industry=body.industry))

    await db.flush()
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
        plan=plan.value,
    )


@router.post("/signin", response_model=TokenResponse)
async def signin(body: SigninRequest, db: DbSession):
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.email == body.email.lower())
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    plan = user.subscription.plan_tier.value if user.subscription else None
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token, user_id=user.id, role=user.role.value, plan=plan
    )


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    # Always succeed — do not leak account existence
    return {
        "message": "If an account exists for that email, password reset instructions have been sent."
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest, user: CurrentUser, db: DbSession
):
    # new_password complexity already enforced by ChangePasswordRequest
    row = await db.get(User, user.id)
    if not row or not verify_password(body.current_password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    row.password_hash = hash_password(body.new_password)
    await db.flush()
    return {"message": "Password updated successfully"}


@router.delete("/me")
async def delete_account(user: CurrentUser, db: DbSession):
    # Fetch the user from the database
    row = await db.get(User, user.id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Due to ON DELETE CASCADE at the database level, deleting the user 
    # will cleanly remove all associated records (profiles, resumes, jobs, etc.)
    await db.delete(row)
    await db.commit()
    return {"message": "Account successfully deleted"}
