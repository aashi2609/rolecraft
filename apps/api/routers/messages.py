from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from core.dependencies import CurrentUser, DbSession
from core.messaging_auth import (
    MESSAGING_ERROR_NOT_ELIGIBLE,
    MESSAGING_ERROR_READ_ONLY,
    can_company_message_candidate,
    get_conversation_permission,
)
from core.rate_limit import RATE_LIMITS, get_user_key, limiter
from models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Company,
    Conversation,
    JobPosting,
    Message,
    Notification,
    User,
    UserRole,
)
from schemas import MessageCreate, MessageOut, ThreadOut

router = APIRouter(prefix="/messages", tags=["messages"])


def _messaging_forbidden(reason: str) -> HTTPException:
    """Build a 403 that carries the stable messaging error code."""
    code = getattr(reason, "code", MESSAGING_ERROR_NOT_ELIGIBLE)
    return HTTPException(
        status_code=403,
        detail=str(reason),
        headers={"X-Error-Code": code},
    )


async def _participant_label(db: DbSession, user_id: UUID) -> str:
    user = await db.get(User, user_id)
    if not user:
        return "Former user"
    if not user.is_active:
        return "Former user"
    if user.role == UserRole.company:
        company = await db.scalar(select(Company).where(Company.user_id == user_id))
        if company and company.name:
            return company.name
        return "Unknown"
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if profile and profile.weblinks and profile.weblinks.get("display_name"):
        return profile.weblinks["display_name"]
    # return candidate real name if available
    if profile and profile.weblinks and profile.weblinks.get("full_name"):
        return profile.weblinks["full_name"]
    return "Unknown"


async def _other_party_is_former(db: DbSession, other_user_id: UUID) -> bool:
    """True when the other participant was deleted or deactivated."""
    other_user = await db.get(User, other_user_id)
    return other_user is None or not other_user.is_active


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
        batch_load_experiences,
        batch_load_jobs,
        batch_load_participants,
        get_last_messages_per_conversation,
        get_unread_counts_per_conversation,
    )

    # Query 1: Get all conversations for this user
    if user.role == UserRole.candidate:
        stmt = select(Conversation).where(Conversation.candidate_id == user.id)
    elif user.role == UserRole.company:
        stmt = select(Conversation).where(Conversation.company_id == user.id)
    else:
        return []

    conversations = (
        (await db.execute(stmt.order_by(Conversation.last_message_at.desc()))).scalars().all()
    )

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
        other_user = users.get(other_id)

        if user.role == UserRole.candidate:
            # Other side is company
            company = companies.get(other_id)
            is_former = other_user is None or not other_user.is_active or company is None
            if is_former:
                label = "Former user"
                avatar_url = None
                subtitle = None
            else:
                label = company.name if company.name else "Unknown"
                avatar_url = company.logo_url
                subtitle = company.industry
        else:
            # Other side is candidate
            profile = profiles.get(other_id)
            is_former = other_user is None or not other_user.is_active or profile is None

            if is_former:
                # Deleted or deactivated participant: safe label, no PII
                label = "Former user"
                avatar_url = None
                subtitle = None
            else:
                # Build participant label
                if profile.weblinks and profile.weblinks.get("display_name"):
                    label = profile.weblinks["display_name"]
                elif profile.weblinks and profile.weblinks.get("full_name"):
                    label = profile.weblinks["full_name"]
                else:
                    label = "Unknown"

                avatar_url = profile.photo_url

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


@router.post("/threads", response_model=MessageOut, status_code=201)
@limiter.limit(RATE_LIMITS["messages_user"], key_func=get_user_key)
async def start_thread(
    request: Request,
    response: Response,
    body: MessageCreate,
    user: CurrentUser,
    db: DbSession,
):
    if user.role != UserRole.company:
        raise HTTPException(
            status_code=403,
            detail="Only companies can start conversations",
            headers={"X-Error-Code": "candidate_cannot_initiate"},
        )

    candidate_id = body.recipient_id
    if not candidate_id:
        raise HTTPException(status_code=400, detail="recipient_id is required")

    # Use centralized authorization
    allowed, reason = await can_company_message_candidate(user.id, candidate_id, db)
    if not allowed:
        raise _messaging_forbidden(reason)

    # Get the application to find the job_id
    app = await db.scalar(
        select(Application)
        .join(JobPosting)
        .where(
            Application.candidate_id == candidate_id,
            JobPosting.company_id == user.id,
            or_(
                Application.status == ApplicationStatus.applied,
                Application.status == ApplicationStatus.shortlisted,
                Application.status == ApplicationStatus.interview,
            ),
        )
    )

    # Get or create conversation (one per company/candidate pair).
    # A concurrent create loses the unique-constraint race; on IntegrityError
    # we roll back and re-read the winner's conversation instead of erroring.
    conv = await db.scalar(
        select(Conversation).where(
            Conversation.company_id == user.id,
            Conversation.candidate_id == candidate_id,
        )
    )
    if not conv:
        conv = Conversation(
            company_id=user.id,
            candidate_id=candidate_id,
            job_id=app.job_id if app else None,
        )
        db.add(conv)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            conv = await db.scalar(
                select(Conversation).where(
                    Conversation.company_id == user.id,
                    Conversation.candidate_id == candidate_id,
                )
            )
            if conv is None:
                raise

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body.strip()[:2000],
    )
    db.add(msg)
    conv.last_message_at = sa.func.now()

    # Create notification for recipient
    notif = Notification(
        user_id=candidate_id,
        type="new_message",
        body="You received a new message regarding a job application.",
        related_id=str(conv.id),
        is_read=False,
    )
    db.add(notif)

    await db.commit()
    await db.refresh(msg)

    return msg


def _encode_message_cursor(sent_at: datetime, message_id: UUID) -> str:
    """Keyset cursor for message history: '<iso sent_at>|<message id>'."""
    return f"{sent_at.isoformat()}|{message_id}"


def _decode_message_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        sent_at_raw, message_id_raw = cursor.rsplit("|", 1)
        return datetime.fromisoformat(sent_at_raw), UUID(message_id_raw)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid cursor")


@router.get("/threads/{id}", response_model=list[MessageOut])
async def get_thread(
    id: UUID,
    user: CurrentUser,
    db: DbSession,
    limit: int | None = Query(None, ge=1, le=500),
    cursor: str | None = Query(None),
):
    """Message history for a thread, ordered by (sent_at, id).

    Keyset pagination (Step 7C): pass ``limit`` plus the ``cursor`` returned
    by the previous page to fetch the next page. Without parameters the full
    history is returned (legacy contract used by the web client).
    """
    allowed, reason = await get_conversation_permission(user.id, user.role, id, db)
    if not allowed:
        raise HTTPException(status_code=404, detail=reason)

    # Mark messages as read
    await db.execute(
        sa.update(Message)
        .where(
            Message.conversation_id == id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=sa.func.now())
    )
    await db.commit()

    stmt = (
        select(Message)
        .where(Message.conversation_id == id)
        .order_by(Message.sent_at.asc(), Message.id.asc())
    )

    if cursor is not None:
        cursor_sent_at, cursor_id = _decode_message_cursor(cursor)
        stmt = stmt.where(
            or_(
                Message.sent_at > cursor_sent_at,
                sa.and_(
                    Message.sent_at == cursor_sent_at,
                    Message.id > cursor_id,
                ),
            )
        )

    if limit is not None:
        stmt = stmt.limit(limit + 1)

    msgs = (await db.execute(stmt)).scalars().all()

    # Trim the lookahead row; caller derives the next cursor from the last
    # returned message when the page came back full.
    has_more = limit is not None and len(msgs) > limit
    if has_more:
        msgs = msgs[:limit]

    return msgs


@router.post("/threads/{id}", response_model=MessageOut, status_code=201)
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

    # Threads with a deleted or deactivated participant are read-only.
    other_id = conv.candidate_id if user.role == UserRole.company else conv.company_id
    if await _other_party_is_former(db, other_id):
        raise HTTPException(
            status_code=403,
            detail="This conversation is read-only because the other participant is no longer active.",
            headers={"X-Error-Code": MESSAGING_ERROR_READ_ONLY},
        )

    # Company replying must have an active plan that includes messaging.
    # The applicant/shortlist relationship is only required to START a
    # conversation, not to reply inside an existing one.
    if user.role == UserRole.company:
        allowed, reason = await can_company_message_candidate(
            user.id, conv.candidate_id, db, check_relationship=False
        )
        if not allowed:
            raise _messaging_forbidden(reason)

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body.strip()[:2000],
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
        is_read=False,
    )
    db.add(notif)

    await db.commit()
    await db.refresh(msg)
    return MessageOut.model_validate(msg)
