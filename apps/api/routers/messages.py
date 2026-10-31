from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Response
import sqlalchemy as sa
from sqlalchemy import or_, select, and_

from core.dependencies import CurrentUser, DbSession
from core.rate_limit import RATE_LIMITS, get_user_key, limiter
from core.messaging_auth import can_company_message_candidate, get_conversation_permission
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
    """Get all message threads for current user with optimized batch loading.
    
    Optimized to fetch all supplementary data in fixed 6 queries:
    1. Conversations
    2. Last messages per conversation
    3. Unread counts
    4. Companies + Candidate profiles
    5. Users
    6. Latest experiences
    7. Related jobs (if any)
    
    Query count is constant regardless of result set size.
    """
    from services.message_thread_service import (
        get_last_messages_per_conversation,
        get_unread_counts_per_conversation,
        batch_load_participants,
        batch_load_experiences,
        batch_load_jobs,
    )
    
    # Query 1: Get all conversations for this user
    if user.role == UserRole.candidate:
        stmt = select(Conversation).where(Conversation.candidate_id == user.id)
    elif user.role == UserRole.company:
        stmt = select(Conversation).where(Conversation.company_id == user.id)
    else:
        return []
    
    conversations = (await db.execute(stmt.order_by(Conversation.last_message_at.desc()))).scalars().all()
    
    if not conversations:
        return []
    
    # Extract IDs for batch queries
    conv_ids = [c.id for c in conversations]
    user_ids = []
    candidate_ids = []
    job_ids = []
    
    for conv in conversations:
        # Determine other user's ID
        other_id = conv.company_id if user.role == UserRole.candidate else conv.candidate_id
        user_ids.append(other_id)
        
        if user.role == UserRole.company:
            candidate_ids.append(conv.candidate_id)
        
        if conv.job_id:
            job_ids.append(conv.job_id)
    
    # Batch load all supplementary data
    # Query 2: Last messages
    last_messages = await get_last_messages_per_conversation(db, conv_ids)
    
    # Query 3: Unread counts
    unread_counts = await get_unread_counts_per_conversation(db, conv_ids, user.id)
    
    # Query 4-6: Participants, experiences, jobs
    companies, profiles, users = await batch_load_participants(db, user_ids)
    experiences = await batch_load_experiences(db, candidate_ids) if candidate_ids else {}
    jobs = await batch_load_jobs(db, job_ids) if job_ids else {}
    
    # Single serialization pass with all data pre-loaded
    out: list[ThreadOut] = []
    for conv in conversations:
        other_id = conv.company_id if user.role == UserRole.candidate else conv.candidate_id
        
        # Get participant info from pre-loaded dicts
        if user.role == UserRole.candidate:
            # Other side is company
            company = companies.get(other_id)
            label = company.name if company and company.name else (users.get(other_id).email if other_id in users else "Unknown")
            avatar_url = company.logo_url if company else None
            subtitle = company.industry if company else None
        else:
            # Other side is candidate
            profile = profiles.get(other_id)
            user_obj = users.get(other_id)
            
            # Build participant label
            if profile and profile.weblinks and profile.weblinks.get("display_name"):
                label = profile.weblinks["display_name"]
            elif profile and profile.full_name:
                label = profile.full_name
            else:
                label = user_obj.email if user_obj else "Unknown"
            
            avatar_url = profile.photo_url if profile else None
            
            # Get latest designation for subtitle
            exp = experiences.get(conv.candidate_id)
            subtitle = exp.designation if exp and exp.designation else None
        
        # Get job title if conversation is linked to a job
        job_title = None
        if conv.job_id and conv.job_id in jobs:
            job = jobs[conv.job_id]
            job_title = job.title or job.job_role
        
        # Get last message preview
        last_msg = last_messages.get(conv.id)
        
        out.append(
            ThreadOut(
                thread_id=conv.id,
                last_body=last_msg.body if last_msg else None,
                last_sent_at=conv.last_message_at,
                participant_label=label,
                other_user_id=other_id,
                unread_count=unread_counts.get(conv.id, 0),
                avatar_url=avatar_url,
                job_title=job_title,
                subtitle=subtitle,
            )
        )
    
    return out


@router.post("/threads", response_model=MessageOut)
@limiter.limit(RATE_LIMITS["messages_user"], key_func=get_user_key)
async def start_thread(
    request: Request,
    response: Response,
    body: MessageCreate,
    user: CurrentUser,
    db: DbSession,
):
    if user.role != UserRole.company:
        raise HTTPException(status_code=403, detail="Only companies can start conversations")
        
    candidate_id = body.recipient_id
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id (recipient_id) is required")

    # Use centralized authorization
    allowed, reason = await can_company_message_candidate(user.id, candidate_id, db)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # Get the application to find the job_id
    app = await db.scalar(
        select(Application).join(JobPosting).where(
            Application.candidate_id == candidate_id,
            JobPosting.company_id == user.id,
            or_(Application.status == ApplicationStatus.applied, Application.status == ApplicationStatus.shortlisted, Application.status == ApplicationStatus.interview)
        )
    )

    # Get or create conversation
    conv = await db.scalar(select(Conversation).where(Conversation.company_id == user.id, Conversation.candidate_id == candidate_id))
    if not conv:
        conv = Conversation(company_id=user.id, candidate_id=candidate_id, job_id=app.job_id if app else None)
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
        body="You received a new message regarding a job application.",
        related_id=str(conv.id),
        is_read=False
    )
    db.add(notif)
    
    await db.commit()
    await db.refresh(msg)
    
    return msg


@router.get("/threads/{id}", response_model=list[MessageOut])
async def get_thread(id: UUID, user: CurrentUser, db: DbSession):
    allowed, reason = await get_conversation_permission(user.id, user.role, id, db)
    if not allowed:
        raise HTTPException(status_code=404, detail=reason)
        
    # Mark messages as read
    await db.execute(
        sa.update(Message).where(Message.conversation_id == id, Message.sender_id != user.id, Message.read_at.is_(None)).values(read_at=sa.func.now())
    )
    await db.commit()

    msgs = (await db.execute(select(Message).where(Message.conversation_id == id).order_by(Message.sent_at.asc()))).scalars().all()
    return msgs


@router.post("/threads/{id}", response_model=MessageOut)
@limiter.limit(RATE_LIMITS["messages_user"], key_func=get_user_key)
async def reply_thread(
    request: Request,
    response: Response,
    id: UUID,
    body: MessageCreate,
    user: CurrentUser,
    db: DbSession,
):
    allowed, reason = await get_conversation_permission(user.id, user.role, id, db)
    if not allowed:
        raise HTTPException(status_code=404, detail=reason)

    conv = await db.get(Conversation, id)
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
        body="You received a new message.",
        related_id=str(conv.id),
        is_read=False
    )
    db.add(notif)
    
    await db.commit()
    await db.refresh(msg)
    return MessageOut.model_validate(msg)
