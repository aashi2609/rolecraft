from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy import select

from core.dependencies import CurrentUser, DbSession
from models import Notification, Subscription, UserRole, PlanTier, SubscriptionStatus
from schemas import NotificationOut, SubscriptionOut, SubscriptionCreate, UploadOut
from services.storage_service import upload_file

router_notifications = APIRouter(prefix="/notifications", tags=["notifications"])
router_subscriptions = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
router_uploads = APIRouter(prefix="/uploads", tags=["uploads"])


@router_notifications.get("/me", response_model=list[NotificationOut])
async def list_notifications(user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [NotificationOut.model_validate(r) for r in rows]


@router_notifications.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(notification_id: UUID, user: CurrentUser, db: DbSession):
    row = await db.get(Notification, notification_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    row.is_read = True
    await db.flush()
    return NotificationOut.model_validate(row)


@router_subscriptions.get("/me", response_model=SubscriptionOut)
async def get_subscription(user: CurrentUser, db: DbSession):
    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active)
        .order_by(Subscription.started_at.desc())
    )
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    return SubscriptionOut.model_validate(sub)


@router_subscriptions.post("", response_model=SubscriptionOut)
async def upsert_subscription(body: SubscriptionCreate, user: CurrentUser, db: DbSession):
    try:
        tier = PlanTier(body.plan_tier.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid plan_tier") from exc

    # Validate plan tier matches user role
    if user.role == UserRole.candidate and tier not in [PlanTier.free, PlanTier.basic, PlanTier.premium, PlanTier.elite]:
        raise HTTPException(status_code=400, detail="Invalid plan tier for candidate role")
    if user.role == UserRole.company and tier not in [PlanTier.starter, PlanTier.growth, PlanTier.scale]:
        raise HTTPException(status_code=400, detail="Invalid plan tier for company role")

    # Cancel existing active subscriptions
    existing = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active
            )
        )
    ).scalars().all()
    for s in existing:
        s.status = SubscriptionStatus.cancelled

    # Create new subscription
    sub = Subscription(
        user_id=user.id,
        role=user.role,
        plan_tier=tier,
        status=SubscriptionStatus.active,
        renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return SubscriptionOut.model_validate(sub)


def _content_length(request: Request) -> int | None:
    raw = request.headers.get("content-length")
    if raw and raw.isdigit():
        return int(raw)
    return None


@router_uploads.post("/photo", response_model=UploadOut)
async def upload_photo(request: Request, user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(
        file,
        prefix=f"photos/{user.id}",
        owner_id=str(user.id),
        category="photo",
        content_length=_content_length(request),
    )
    return UploadOut(url=url, path=path)


@router_uploads.post("/document", response_model=UploadOut)
async def upload_document(request: Request, user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(
        file,
        prefix=f"documents/{user.id}",
        owner_id=str(user.id),
        category="document",
        content_length=_content_length(request),
    )
    return UploadOut(url=url, path=path)


@router_uploads.post("/logo", response_model=UploadOut)
async def upload_logo(request: Request, user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(
        file,
        prefix=f"photos/{user.id}",
        owner_id=str(user.id),
        category="photo",
        content_length=_content_length(request),
    )
    return UploadOut(url=url, path=path)
