"""Message thread service with optimized batch loading (Step 7B).

Batch loads all supplementary data for message threads in fixed number of queries,
eliminating N+1 patterns from list_threads endpoint.
"""

from uuid import UUID
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from models import (
    Message, Conversation, Company, CandidateProfile, User, Experience,
    JobPosting, UserRole
)


async def get_last_messages_per_conversation(db, conversation_ids: list[UUID]) -> dict:
    """
    Fetch last message per conversation in a single query.
    Uses PostgreSQL DISTINCT ON for efficiency.
    
    Returns: { conversation_id: Message, ... }
    """
    if not conversation_ids:
        return {}
    
    # PostgreSQL: DISTINCT ON (partition_column)
    # Returns only the first row (ordered by desc) for each conversation
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id.in_(conversation_ids))
        .distinct(Message.conversation_id)
        .order_by(Message.conversation_id, desc(Message.sent_at))
    )
    
    last_messages = {}
    for msg in result.scalars().all():
        # Only keep the first (= most recent due to order_by)
        if msg.conversation_id not in last_messages:
            last_messages[msg.conversation_id] = msg
    
    return last_messages


async def get_unread_counts_per_conversation(
    db, conversation_ids: list[UUID], current_user_id: UUID
) -> dict:
    """
    Fetch unread message count per conversation in a single grouped query.
    Unread = messages not sent by current user and with read_at = NULL.
    
    Returns: { conversation_id: int, ... }
    """
    if not conversation_ids:
        return {}
    
    result = await db.execute(
        select(
            Message.conversation_id,
            func.count(Message.id).label('unread_count')
        )
        .where(
            Message.conversation_id.in_(conversation_ids),
            Message.sender_id != current_user_id,
            Message.read_at.is_(None)
        )
        .group_by(Message.conversation_id)
    )
    
    unread = {}
    for row in result.all():
        unread[row.conversation_id] = row.unread_count or 0
    
    # Ensure all conversations have an entry
    for conv_id in conversation_ids:
        if conv_id not in unread:
            unread[conv_id] = 0
    
    return unread


async def batch_load_participants(
    db, user_ids: list[UUID]
) -> tuple[dict, dict, dict]:
    """
    Batch-load all Companies, CandidateProfiles, and Users.
    
    Returns: (companies_dict, profiles_dict, users_dict)
        - companies_dict: { user_id: Company, ... }
        - profiles_dict: { user_id: CandidateProfile, ... }
        - users_dict: { user_id: User, ... }
    """
    if not user_ids:
        return {}, {}, {}
    
    # Fetch all companies
    companies_result = await db.execute(
        select(Company).where(Company.user_id.in_(user_ids))
    )
    companies_dict = {c.user_id: c for c in companies_result.scalars().all()}
    
    # Fetch all candidate profiles
    profiles_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id.in_(user_ids))
    )
    profiles_dict = {p.user_id: p for p in profiles_result.scalars().all()}
    
    # Fetch all users
    users_result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users_dict = {u.id: u for u in users_result.scalars().all()}
    
    return companies_dict, profiles_dict, users_dict


async def batch_load_experiences(
    db, candidate_ids: list[UUID]
) -> dict:
    """
    Batch-load latest experience per candidate.
    Uses DISTINCT ON to get most recent (ordered by from_date DESC).
    
    Returns: { candidate_id: Experience, ... }
    """
    if not candidate_ids:
        return {}
    
    result = await db.execute(
        select(Experience)
        .where(Experience.candidate_id.in_(candidate_ids))
        .distinct(Experience.candidate_id)
        .order_by(Experience.candidate_id, desc(Experience.from_date.nullslast()))
    )
    
    experiences = {}
    for exp in result.scalars().all():
        # Only keep the first (= most recent)
        if exp.candidate_id not in experiences:
            experiences[exp.candidate_id] = exp
    
    return experiences


async def batch_load_jobs(
    db, job_ids: list[UUID]
) -> dict:
    """
    Batch-load all jobs.
    
    Returns: { job_id: JobPosting, ... }
    """
    if not job_ids:
        return {}
    
    result = await db.execute(
        select(JobPosting).where(JobPosting.id.in_(job_ids))
    )
    return {j.id: j for j in result.scalars().all()}
