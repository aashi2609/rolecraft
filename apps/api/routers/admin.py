from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from core.dependencies import DbSession, get_current_user
from models import User, UserRole, Subscription
from schemas import UserOut, SubscriptionOut
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/me")
async def get_me(current_admin: User = Depends(get_current_admin)) -> Any:
    return {"status": "ok", "role": "admin"}

@router.get("/users", response_model=List[UserOut])
async def get_all_users(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

class UserStatusUpdate(BaseModel):
    role: str

@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    update_data: UserStatusUpdate,
    db: DbSession,
    current_admin: User = Depends(get_current_admin)
) -> Any:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = update_data.role
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/subscriptions", response_model=List[SubscriptionOut])
async def get_all_subscriptions(
    db: DbSession,
    current_admin: User = Depends(get_current_admin),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    result = await db.execute(select(Subscription).offset(skip).limit(limit))
    return result.scalars().all()

@router.patch("/subscriptions/{sub_id}")
async def update_subscription(
    sub_id: str,
    plan_tier: str,
    db: DbSession,
    current_admin: User = Depends(get_current_admin)
) -> Any:
    sub = await db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.plan_tier = plan_tier
    await db.commit()
    await db.refresh(sub)
    return sub
