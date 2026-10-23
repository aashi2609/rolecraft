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
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from models import (
    User,
    UserRole,
)
from schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    RefreshTokenRequest,
    SigninRequest,
    SignupRequest,
    TokenResponse,
)
from services.account_deletion_service import delete_user_account
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
    token = create_access_token(
        user_id=user.id, role=user.role.value, token_version=user.token_version
    )
    refresh_token = create_refresh_token(
        user_id=user.id, token_version=user.token_version
    )
    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
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
    token = create_access_token(
        user_id=user.id, role=user.role.value, token_version=user.token_version
    )
    refresh_token = create_refresh_token(
        user_id=user.id, token_version=user.token_version
    )
    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role.value,
        plan=plan,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshTokenRequest, db: DbSession
):
    """Rotate access token and refresh token using a valid refresh token."""
    try:
        payload = decode_refresh_token(body.refresh_token)
        from uuid import UUID
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    token_version = payload.get("token_version")
    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or deleted"
        )

    if token_version is not None and user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked"
        )

    # Issue new access and rotated refresh token
    plan = user.subscription.plan_tier.value if user.subscription else None
    new_token = create_access_token(
        user_id=user.id, role=user.role.value, token_version=user.token_version
    )
    new_refresh = create_refresh_token(
        user_id=user.id, token_version=user.token_version
    )
    return TokenResponse(
        access_token=new_token,
        refresh_token=new_refresh,
        user_id=user.id,
        role=user.role.value,
        plan=plan,
    )


@router.post("/logout")
async def logout(user: CurrentUser, db: DbSession):
    """Log out everywhere: increment token_version to invalidate all existing tokens server-side."""
    row = await db.get(User, user.id)
    if row:
        row.token_version += 1
        await db.commit()
    return {"message": "Successfully logged out everywhere"}


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
    # Increment token_version so all existing sessions/tokens die immediately
    row.token_version += 1
    await db.flush()
    return {"message": "Password updated successfully"}


@router.delete("/me")
@limiter.limit(RATE_LIMITS["delete_account_user"], key_func=get_user_key)
async def delete_account(
    request: Request,
    response: Response,
    body: DeleteAccountRequest,
    user: CurrentUser,
    db: DbSession,
):
    # Fetch the user from the database
    row = await db.get(User, user.id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 1. Verify current password
    if not verify_password(body.current_password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # 2. Verify explicit confirmation string
    if body.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation text must be 'DELETE'",
        )

    # 3. Clean up all stored files and cascade delete user record
    await delete_user_account(db, user.id)
    await db.commit()
    return {"message": "Account successfully deleted"}
