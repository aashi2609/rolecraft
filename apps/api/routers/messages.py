from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from core.dependencies import CurrentUser, DbSession
from models import CandidateProfile, Company, Message, User, UserRole
from schemas import MessageCreate, MessageOut, ThreadOut

router = APIRouter(prefix="/messages", tags=["messages"])


async def _participant_label(db, user_id: UUID) -> str:
    user = await db.get(User, user_id)
    if not user:
        return "User"
    if user.role == UserRole.company:
        company = await db.scalar(select(Company).where(Company.user_id == user_id))
        return company.name if company and company.name else user.email
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if profile and profile.weblinks and profile.weblinks.get("display_name"):
        return profile.weblinks["display_name"]
    return user.email


def _user_participates(msg: Message, user_id: UUID) -> bool:
    return msg.sender_id == user_id or msg.recipient_id == user_id


@router.get("/threads", response_model=list[ThreadOut])
async def list_threads(user: CurrentUser, db: DbSession):
    thread_ids = (
        await db.execute(
            select(Message.thread_id)
            .where(or_(Message.sender_id == user.id, Message.recipient_id == user.id))
            .distinct()
        )
    ).scalars().all()

    out: list[ThreadOut] = []
    for tid in thread_ids:
        msgs = (
            await db.execute(
                select(Message).where(Message.thread_id == tid).order_by(Message.sent_at.desc())
            )
        ).scalars().all()
        if not msgs:
            continue
        last = msgs[0]
        other_id = None
        for m in msgs:
            if m.sender_id != user.id:
                other_id = m.sender_id
                break
            if m.recipient_id and m.recipient_id != user.id:
                other_id = m.recipient_id
                break
        label = await _participant_label(db, other_id) if other_id else "Conversation"
        out.append(
            ThreadOut(
                thread_id=tid,
                last_body=last.body,
                last_sent_at=last.sent_at,
                participant_label=label,
                other_user_id=other_id,
            )
        )
    out.sort(key=lambda t: t.last_sent_at or t.thread_id, reverse=True)
    return out


@router.post("/threads", response_model=MessageOut)
async def start_thread(body: MessageCreate, user: CurrentUser, db: DbSession):
    if not body.recipient_id:
        raise HTTPException(status_code=400, detail="recipient_id is required to start a thread")
    recipient = await db.get(User, body.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    msg = Message(
        thread_id=uuid4(),
        sender_id=user.id,
        recipient_id=body.recipient_id,
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
    if not any(_user_participates(m, user.id) for m in msgs):
        raise HTTPException(status_code=403, detail="Not a participant in this thread")
    return [MessageOut.model_validate(m) for m in msgs]


@router.post("/threads/{thread_id}", response_model=MessageOut)
async def send_message(thread_id: UUID, body: MessageCreate, user: CurrentUser, db: DbSession):
    existing = (
        await db.execute(select(Message).where(Message.thread_id == thread_id).limit(1))
    ).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not _user_participates(existing, user.id):
        raise HTTPException(status_code=403, detail="Not a participant in this thread")

    recipient_id = body.recipient_id
    if not recipient_id:
        first = (
            await db.execute(
                select(Message).where(Message.thread_id == thread_id).order_by(Message.sent_at.asc())
            )
        ).scalars().first()
        if first:
            recipient_id = first.recipient_id if first.sender_id == user.id else first.sender_id

    msg = Message(
        thread_id=thread_id,
        sender_id=user.id,
        recipient_id=recipient_id,
        sender_role=user.role,
        body=body.body,
    )
    db.add(msg)
    await db.flush()
    return MessageOut.model_validate(msg)
