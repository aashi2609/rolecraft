from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy import select

from core.dependencies import CurrentUser, DbSession
from models import Notification, Subscription, UserRole, PlanTier, SubscriptionStatus
from schemas import NotificationOut, SubscriptionOut, SubscriptionCreate, UploadOut
from services.storage_service import upload_file
from services.subscription_service import get_active_subscription, upsert_subscription

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
    sub = await get_active_subscription(db, user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    return SubscriptionOut.model_validate(sub)


@router_subscriptions.post("", response_model=SubscriptionOut)
async def upsert_subscription_route(body: SubscriptionCreate, user: CurrentUser, db: DbSession):
    return await upsert_subscription(db, body, user.id, user.role)


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
