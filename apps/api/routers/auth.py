from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CurrentUser, DbSession
from core.rate_limit import (
    RATE_LIMITS,
    enforce_limit,
    get_user_key,
    limiter,
)
from core.security import create_access_token, hash_password, verify_password
from models import (
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
from services.user_service import create_user_with_profile, parse_plan

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
@limiter.limit(RATE_LIMITS["signup_ip"])
async def signup(
    request: Request, response: Response, body: SignupRequest, db: DbSession
):
    # Password complexity + role Literal already enforced by SignupRequest
    role = UserRole(body.role)
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await create_user_with_profile(
        db=db,
        email=body.email,
        password=body.password,
        role=role,
        name=body.name,
        industry=body.industry,
        plan=body.plan,
    )
    plan = parse_plan(body.plan, role)
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
        plan=plan.value,
    )


@router.post("/signin", response_model=TokenResponse)
@limiter.limit(RATE_LIMITS["signin_ip"])
async def signin(
    request: Request, response: Response, body: SigninRequest, db: DbSession
):
    email = body.email.lower()
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        # Per-email failed-attempt budget (does not reveal whether the email exists)
        enforce_limit("signin_email_failed", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    # Deactivated users cannot sign in — use the same generic message
    # to prevent account-state enumeration.
    if not user.is_active:
        enforce_limit("signin_email_failed", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    plan = user.subscription.plan_tier.value if user.subscription else None
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token, user_id=user.id, role=user.role.value, plan=plan
    )


@router.post("/forgot-password")
@limiter.limit(RATE_LIMITS["forgot_password_ip"])
async def forgot_password(
    request: Request, response: Response, body: ForgotPasswordRequest
):
    # Per-email cap (always applied — do not leak account existence)
    enforce_limit("forgot_password_email", body.email.lower())
    # Always succeed — do not leak account existence
    return {
        "message": "If an account exists for that email, password reset instructions have been sent."
    }


# Future: POST /auth/reset-password should use:
#   @limiter.limit(RATE_LIMITS["reset_password_ip"])
#   enforce_limit("reset_password_email", email)
# via enforce_reset_password_limits() in core.rate_limit


@router.post("/change-password")
@limiter.limit(RATE_LIMITS["change_password_user"], key_func=get_user_key)
async def change_password(
    request: Request,
    response: Response,
    body: ChangePasswordRequest,
    user: CurrentUser,
    db: DbSession,
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
@limiter.limit(RATE_LIMITS["delete_account_user"], key_func=get_user_key)
async def delete_account(
    request: Request, response: Response, user: CurrentUser, db: DbSession
):
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
