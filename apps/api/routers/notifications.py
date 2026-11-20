from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import select

from core.dependencies import CurrentUser, DbSession
from core.rate_limit import RATE_LIMITS, get_user_key, limiter
from models import Notification
from schemas import NotificationOut, SubscriptionCreate, SubscriptionOut, UploadOut
from services.storage_service import upload_file
from services.subscription_service import upsert_subscription

router_notifications = APIRouter(prefix="/notifications", tags=["notifications"])
router_subscriptions = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
router_uploads = APIRouter(prefix="/uploads", tags=["uploads"])


@router_notifications.get("/me", response_model=list[NotificationOut])
async def list_notifications(user: CurrentUser, db: DbSession):
    rows = (
        (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [NotificationOut.model_validate(r) for r in rows]


@router_notifications.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(notification_id: UUID, user: CurrentUser, db: DbSession):
    row = await db.get(Notification, notification_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    row.is_read = True
    await db.flush()
    return NotificationOut.model_validate(row)


@router_subscriptions.get("/me")
async def get_subscription(user: CurrentUser, db: DbSession):
    """Current live subscription. No subscription is a normal state: 200 with
    plan=null, status='none', and no paid entitlements."""
    from services.entitlement_service import PLAN_FEATURES, get_entitlements
    from services.subscription_service import get_current_subscription

    sub = await get_current_subscription(db, user.id)
    entitlements = await get_entitlements(user, db)

    if sub is None:
        return {
            "plan": None,
            "status": "none",
            "entitlements": PLAN_FEATURES["free"]._asdict(),
        }
    return {
        "plan": sub.plan_tier.value if hasattr(sub.plan_tier, "value") else sub.plan_tier,
        "status": sub.status.value if hasattr(sub.status, "value") else sub.status,
        "entitlements": entitlements._asdict(),
        "id": str(sub.id),
        "started_at": sub.started_at.isoformat() if sub.started_at else None,
        "renews_at": sub.renews_at.isoformat() if sub.renews_at else None,
    }


@router_subscriptions.post("", response_model=SubscriptionOut)
async def upsert_subscription_route(body: SubscriptionCreate, user: CurrentUser, db: DbSession):
    return await upsert_subscription(db, body, user.id, user.role)


def _content_length(request: Request) -> int | None:
    raw = request.headers.get("content-length")
    if raw and raw.isdigit():
        return int(raw)
    return None


@router_uploads.post("/photo", response_model=UploadOut)
@limiter.limit(RATE_LIMITS["uploads_user"], key_func=get_user_key)
async def upload_photo(
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    url, path, _ = await upload_file(
        file,
        prefix=f"photos/{user.id}",
        owner_id=str(user.id),
        category="photo",
        content_length=_content_length(request),
        db=db,
    )
    return UploadOut(url=url, path=path)


@router_uploads.post("/document", response_model=UploadOut)
@limiter.limit(RATE_LIMITS["uploads_user"], key_func=get_user_key)
async def upload_document(
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    url, path, _ = await upload_file(
        file,
        prefix=f"documents/{user.id}",
        owner_id=str(user.id),
        category="document",
        content_length=_content_length(request),
        db=db,
    )
    return UploadOut(url=url, path=path)


@router_uploads.post("/logo", response_model=UploadOut)
@limiter.limit(RATE_LIMITS["uploads_user"], key_func=get_user_key)
async def upload_logo(
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    url, path, _ = await upload_file(
        file,
        prefix=f"logos/{user.id}",
        owner_id=str(user.id),
        category="photo",
        content_length=_content_length(request),
        db=db,
    )
    return UploadOut(url=url, path=path)
