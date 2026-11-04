"""Conversation management API.

Step 4D: Company initiates conversations with candidates (applicants or shortlisted).
Messaging policy: applicants_only (company can only message candidates who applied or were shortlisted).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CurrentUser, DbSession
from core.messaging_auth import can_company_message_candidate, get_conversation_permission
from models import (
    Conversation,
    User,
    UserRole,
    CandidateProfile,
    Company,
    Application,
    ApplicationStatus,
)
from schemas import ConversationOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", status_code=201, response_model=ConversationOut)
async def start_conversation(
    candidate_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Company starts a conversation with a candidate.
    
    Only company role can initiate (403 for candidates, 404 for others).
    Checks messaging policy: applicants_only = must have applied or shortlisted.
    """
    if user.role != UserRole.company:
        if user.role == UserRole.candidate:
            raise HTTPException(status_code=403, detail="Candidates cannot initiate conversations")
        raise HTTPException(status_code=404, detail="Not found")
    
    # Verify candidate exists
    candidate = await db.get(User, candidate_id)
    if not candidate or candidate.role != UserRole.candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check messaging policy
    can_message, reason = await can_company_message_candidate(user.id, candidate_id, db)
    if not can_message:
        raise HTTPException(status_code=403, detail=reason or "Cannot message this candidate")
    
    # Get company
    company = await db.scalar(select(Company).where(Company.user_id == user.id))
    if not company:
        raise HTTPException(status_code=400, detail="Company profile not found")
    
    # Check if conversation already exists (one per pair)
    existing = await db.scalar(
        select(Conversation).where(
            Conversation.company_id == company.user_id,
            Conversation.candidate_id == candidate_id,
        )
    )
    if existing:
        await db.refresh(existing)
        return ConversationOut.model_validate(existing)
    
    # Create new conversation
    conversation = Conversation(
        candidate_id=candidate_id,
        company_id=company.user_id,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Get a conversation by ID (IDOR prevention: verify access)."""
    allowed, reason = await get_conversation_permission(user.id, user.role, conversation_id, db)
    if not allowed:
        raise HTTPException(status_code=404, detail=reason or "Conversation not found")
    
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationOut.model_validate(conversation)


@router.get("", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbSession):
    """List all conversations for the user."""
    if user.role == UserRole.company:
        conversations = await db.scalars(
            select(Conversation)
            .where(Conversation.company_id == user.id)
            .options(selectinload(Conversation.candidate), selectinload(Conversation.company))
        )
    elif user.role == UserRole.candidate:
        conversations = await db.scalars(
            select(Conversation)
            .where(Conversation.candidate_id == user.id)
            .options(selectinload(Conversation.candidate), selectinload(Conversation.company))
        )
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return [ConversationOut.model_validate(c) for c in conversations]
