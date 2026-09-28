import { UUID, uuid4 } from 'uuid' # Wait this is Python...
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import or_, select, and_

from core.dependencies import CurrentUser, DbSession
from models import CandidateProfile, Company, Message, User, UserRole, Conversation, JobPosting, Application, ApplicationStatus, Notification
from schemas import MessageCreate, MessageOut, ThreadOut

router = APIRouter(prefix="/messages", tags=["messages"])


async def _participant_label(db: DbSession, user_id: UUID) -> str:
    user = await db.get(User, user_id)
    if not user:
        return "User"
    if user.role == UserRole.company:
        company = await db.scalar(select(Company).where(Company.user_id == user_id))
        return company.name if company and company.name else user.email
    profile = await db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    if profile and profile.weblinks and profile.weblinks.get("display_name"):
        return profile.weblinks["display_name"]
    # return candidate real name if available, else email
    if profile and profile.full_name:
        return profile.full_name
    return user.email


@router.get("/threads", response_model=list[ThreadOut])
async def list_threads(user: CurrentUser, db: DbSession):
    # Get all conversations for this user
    if user.role == UserRole.candidate:
        stmt = select(Conversation).where(Conversation.candidate_id == user.id)
    elif user.role == UserRole.company:
        stmt = select(Conversation).where(Conversation.company_id == user.id)
    else:
        return []
    
    conversations = (await db.execute(stmt.order_by(Conversation.last_message_at.desc()))).scalars().all()
    
    out: list[ThreadOut] = []
    for conv in conversations:
        # Get last message
        last_msg = await db.scalar(select(Message).where(Message.conversation_id == conv.id).order_by(Message.sent_at.desc()).limit(1))
        
        # Determine the other user's ID
        other_id = conv.company_id if user.role == UserRole.candidate else conv.candidate_id
        label = await _participant_label(db, other_id)
        
        # Calculate unread count
        unread = await db.scalar(select(sa.func.count(Message.id)).where(Message.conversation_id == conv.id, Message.sender_id != user.id, Message.read_at.is_(None)))

        out.append(
            ThreadOut(
                thread_id=conv.id,
                last_body=last_msg.body if last_msg else None,
                last_sent_at=conv.last_message_at,
                participant_label=label,
                other_user_id=other_id,
                unread_count=unread or 0
            )
        )
    return out


@router.post("/threads", response_model=MessageOut)
async def start_thread(body: MessageCreate, user: CurrentUser, db: DbSession):
    if user.role != UserRole.company:
        raise HTTPException(status_code=403, detail="Only companies can start conversations")
        
    candidate_id = body.recipient_id
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id (recipient_id) is required")

    # Authorize: Must have applied or be shortlisted
    # Wait, the user said "A company may START a conversation only with a candidate who applied to one of ITS jobs or whom it has shortlisted."
    app = await db.scalar(
        select(Application).join(JobPosting).where(
            Application.candidate_id == candidate_id,
            JobPosting.company_id == user.id,
            or_(Application.status == ApplicationStatus.applied, Application.status == ApplicationStatus.shortlisted, Application.status == ApplicationStatus.interview)
        )
    )
    if not app:
        raise HTTPException(status_code=403, detail="Cannot message a candidate who has not applied to your jobs")

    # Get or create conversation
    conv = await db.scalar(select(Conversation).where(Conversation.company_id == user.id, Conversation.candidate_id == candidate_id))
    if not conv:
        conv = Conversation(company_id=user.id, candidate_id=candidate_id, job_id=app.job_id)
        db.add(conv)
        await db.flush()

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body.strip()[:2000]
    )
    db.add(msg)
    conv.last_message_at = sa.func.now()
    
    # Create notification for recipient
    notif = Notification(
        user_id=candidate_id,
        type="new_message",
        title="New Message",
        message=f"You received a new message regarding a job application.",
        link=f"/messages",
        read=False
    )
    db.add(notif)
    
    await db.commit()
    await db.refresh(msg)
    
    return msg


@router.get("/threads/{id}", response_model=list[MessageOut])
async def get_thread(id: UUID, user: CurrentUser, db: DbSession):
    conv = await db.get(Conversation, id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if conv.company_id != user.id and conv.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Mark messages as read
    await db.execute(
        sa.update(Message).where(Message.conversation_id == id, Message.sender_id != user.id, Message.read_at.is_(None)).values(read_at=sa.func.now())
    )
    await db.commit()

    msgs = (await db.execute(select(Message).where(Message.conversation_id == id).order_by(Message.sent_at.asc()))).scalars().all()
    return msgs


@router.post("/threads/{id}", response_model=MessageOut)
async def reply_thread(id: UUID, body: MessageCreate, user: CurrentUser, db: DbSession):
    conv = await db.get(Conversation, id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if conv.company_id != user.id and conv.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body.strip()[:2000]
    )
    db.add(msg)
    conv.last_message_at = sa.func.now()
    
    # Create notification for recipient
    recipient_id = conv.company_id if user.role == UserRole.candidate else conv.candidate_id
    notif = Notification(
        user_id=recipient_id,
        type="new_message",
        title="New Message",
        message=f"You received a new message.",
        link=f"/company/messages" if user.role == UserRole.candidate else "/messages",
        read=False
    )
    db.add(notif)
    
    await db.commit()
    await db.refresh(msg)
    return msg    )
    db.add(msg)
    await db.flush()
    return MessageOut.model_validate(msg)


@router.get("/threads/{thread_id}", response_model=list[MessageOut])
async def get_thread(thread_id: UUID, user: CurrentUser, db: DbSession):
    msgs = (
        (
            await db.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.sent_at.asc())
            )
        )
        .scalars()
        .all()
    )
    if not msgs:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not any(_user_participates(m, user.id) for m in msgs):
        raise HTTPException(status_code=403, detail="Not a participant in this thread")
    return [MessageOut.model_validate(m) for m in msgs]


@router.post("/threads/{thread_id}", response_model=MessageOut)
async def send_message(
    thread_id: UUID, body: MessageCreate, user: CurrentUser, db: DbSession
):
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
            (
                await db.execute(
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    .order_by(Message.sent_at.asc())
                )
            )
            .scalars()
            .first()
        )
        if first:
            recipient_id = (
                first.recipient_id if first.sender_id == user.id else first.sender_id
            )

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
