from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from core.dependencies import CurrentUser, DbSession, get_user_plan
from models import Notification, PlanTier, Subscription, SubscriptionStatus
from schemas import NotificationOut, SubscriptionCreate, SubscriptionOut, UploadOut
from services.storage_service import upload_file
from fastapi import File, UploadFile

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

    # Cancel existing
    existing = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active
            )
        )
    ).scalars().all()
    for s in existing:
        s.status = SubscriptionStatus.cancelled

    sub = Subscription(
        user_id=user.id,
        role=user.role,
        plan_tier=tier,
        status=SubscriptionStatus.active,
        renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    await db.flush()
    return SubscriptionOut.model_validate(sub)


@router_uploads.post("/photo", response_model=UploadOut)
async def upload_photo(user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(file, prefix=f"photos/{user.id}", owner_id=str(user.id))
    return UploadOut(url=url, path=path)


@router_uploads.post("/document", response_model=UploadOut)
async def upload_document(user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(file, prefix=f"documents/{user.id}", owner_id=str(user.id))
    return UploadOut(url=url, path=path)


@router_uploads.post("/logo", response_model=UploadOut)
async def upload_logo(user: CurrentUser, file: UploadFile = File(...)):
    url, path = await upload_file(file, prefix=f"logos/{user.id}", owner_id=str(user.id))
    return UploadOut(url=url, path=path)
