"""
Centralized authorization for recruiter-to-candidate messaging.

All messaging routes and UI elements (search, applications, WebSocket) use
can_company_message_candidate() to enforce a consistent, configurable policy.
"""

from uuid import UUID
from enum import Enum
from sqlalchemy import or_, select

from core.config import get_settings
from models import (
    Application,
    ApplicationStatus,
    Conversation,
    JobPosting,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)


class MessagingAuthError(Exception):
    """Exception raised when messaging authorization fails."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class MessagingPolicy(str, Enum):
    """Messaging policies."""
    APPLICANTS_ONLY = "applicants_only"
    ANY_CANDIDATE_WITH_PLAN = "any_candidate_with_plan"


async def can_company_message_candidate(
    company_id: UUID,
    candidate_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Centralized authorization check for company-to-candidate messaging.

    Enforces the configured messaging policy:
    - applicants_only: Company can message candidates who applied to its jobs or shortlisted
    - any_candidate_with_plan: Company can message any candidate if it has active plan

    Args:
        company_id: UUID of the company user
        candidate_id: UUID of the candidate user
        db: Database session

    Returns:
        (allowed: bool, reason: str)
        - If allowed: (True, "")
        - If denied: (False, user_facing_reason_string)

    Examples:
        allowed, reason = await can_company_message_candidate(company_id, candidate_id, db)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason)
    """
    settings = get_settings()
    policy = MessagingPolicy(settings.messaging_policy)

    if policy == MessagingPolicy.APPLICANTS_ONLY:
        return await _check_applicants_only(company_id, candidate_id, db)
    elif policy == MessagingPolicy.ANY_CANDIDATE_WITH_PLAN:
        return await _check_any_candidate_with_plan(company_id, candidate_id, db)
    else:
        raise ValueError(f"Unknown messaging policy: {policy}")


async def _check_applicants_only(
    company_id: UUID,
    candidate_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Check if company can message candidate under 'applicants_only' policy.

    Allowed if:
    1. Candidate has applied to one of company's jobs (status: applied, shortlisted, or interview)
    """
    # Check if candidate has an application to any of company's jobs
    # in an active state (applied, shortlisted, interview)
    app = await db.scalar(
        select(Application).join(JobPosting).where(
            Application.candidate_id == candidate_id,
            JobPosting.company_id == company_id,
            or_(
                Application.status == ApplicationStatus.applied,
                Application.status == ApplicationStatus.shortlisted,
                Application.status == ApplicationStatus.interview,
            ),
        )
    )

    if app:
        return True, ""

    return (
        False,
        "You can message candidates who have applied to your jobs or whom you have shortlisted.",
    )


async def _check_any_candidate_with_plan(
    company_id: UUID,
    candidate_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Check if company can message candidate under 'any_candidate_with_plan' policy.

    Allowed if:
    1. Company has an active subscription plan
    2. Candidate exists and is active
    """
    # Get company user
    company_user = await db.get(User, company_id)
    if not company_user or company_user.role != UserRole.company:
        return False, "Invalid company."

    # Check if company has active subscription
    subscription = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == company_id,
            Subscription.status == SubscriptionStatus.active,
        )
    )

    if not subscription:
        return False, "You need an active subscription to message candidates. Upgrade your plan."

    # Check if candidate exists and is active
    candidate_user = await db.get(User, candidate_id)
    if not candidate_user or candidate_user.role != UserRole.candidate or not candidate_user.is_active:
        return False, "This candidate is not available."

    return True, ""


async def candidate_can_reply_to_thread(
    candidate_id: UUID,
    conversation_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Check if candidate can reply to an existing conversation.

    Allowed if:
    1. Candidate is a participant in the conversation
    """
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        return False, "Conversation not found."

    if conv.candidate_id != candidate_id:
        return False, "Conversation not found."

    return True, ""


async def get_conversation_permission(
    user_id: UUID,
    user_role: UserRole,
    conversation_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Check if user can view/reply to a conversation.

    Allowed if:
    1. User is a participant in the conversation
    """
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        return False, "Conversation not found."

    is_participant = (
        (user_role == UserRole.company and conv.company_id == user_id)
        or (user_role == UserRole.candidate and conv.candidate_id == user_id)
    )

    if not is_participant:
        return False, "Conversation not found."

    return True, ""
