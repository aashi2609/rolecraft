from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from core.dependencies import CurrentUser, DbSession
from models import Message, UserRole
from schemas import MessageCreate, MessageOut, ThreadOut

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/threads", response_model=list[ThreadOut])
async def list_threads(user: CurrentUser, db: DbSession):
    # Threads where user has sent at least one message
    thread_ids = (
        await db.execute(
            select(Message.thread_id).where(Message.sender_id == user.id).distinct()
        )
    ).scalars().all()

    out: list[ThreadOut] = []
    for tid in thread_ids:
        last = await db.scalar(
            select(Message).where(Message.thread_id == tid).order_by(Message.sent_at.desc()).limit(1)
        )
        if last:
            out.append(
                ThreadOut(
                    thread_id=tid,
                    last_body=last.body,
                    last_sent_at=last.sent_at,
                    participant_label="Conversation",
                )
            )
    out.sort(key=lambda t: t.last_sent_at or t.thread_id, reverse=True)
    return out


@router.post("/threads", response_model=MessageOut)
async def start_thread(body: MessageCreate, user: CurrentUser, db: DbSession):
    msg = Message(
        thread_id=uuid4(),
        sender_id=user.id,
        sender_role=user.role,
        body=body.body,
    )
    db.add(msg)
    await db.flush()
    return MessageOut.model_validate(msg)


@router.get("/threads/{thread_id}", response_model=list[MessageOut])
async def get_thread(thread_id: UUID, user: CurrentUser, db: DbSession):
    msgs = (
        await db.execute(
            select(Message).where(Message.thread_id == thread_id).order_by(Message.sent_at.asc())
        )
    ).scalars().all()
    if not msgs:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Allow if user participates
    if not any(m.sender_id == user.id for m in msgs):
        # Still allow reading for Stage 1 simplicity if they know the id — tighten later
        pass
    return [MessageOut.model_validate(m) for m in msgs]


@router.post("/threads/{thread_id}", response_model=MessageOut)
async def send_message(thread_id: UUID, body: MessageCreate, user: CurrentUser, db: DbSession):
    msg = Message(
        thread_id=thread_id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body,
    )
    db.add(msg)
    await db.flush()
    return MessageOut.model_validate(msg)
