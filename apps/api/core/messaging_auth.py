"""
Centralized authorization for recruiter-to-candidate messaging.

All messaging routes and UI elements (search, applications, WebSocket) use
can_company_message_candidate() to enforce a consistent, configurable policy.
"""

from enum import Enum
from uuid import UUID

from sqlalchemy import or_, select

from core.config import get_settings
from models import (
    Application,
    ApplicationStatus,
    Conversation,
    JobPosting,
    User,
    UserRole,
)
from services.entitlement_service import PLAN_FEATURES, get_entitlements


class MessagingDenial(str):
    """User-facing denial reason that also carries a stable error code.

    Behaves as a plain ``str`` (all existing ``in`` / ``.lower()`` checks keep
    working) while exposing ``.code`` for the router to forward as the
    ``X-Error-Code`` response header.
    """

    code: str

    def __new__(cls, message: str, code: str = "messaging_denied"):
        obj = super().__new__(cls, message)
        obj.code = code
        return obj


MESSAGING_ERROR_PLAN_REQUIRED = "plan_required"
MESSAGING_ERROR_NOT_ELIGIBLE = "not_eligible"
MESSAGING_ERROR_READ_ONLY = "read_only"


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
    check_relationship: bool = True,
) -> tuple[bool, str]:
    """
    Centralized authorization check for company-to-candidate messaging.

    Enforces the configured messaging policy:
    - applicants_only: Company can message candidates who applied to its jobs or shortlisted
    - any_candidate_with_plan: Company can message any candidate if it has active plan

    CRITICAL: Sending a NEW message requires an active company subscription.
    Reading existing conversations never requires a subscription.

    Args:
        company_id: UUID of the company user
        candidate_id: UUID of the candidate user
        db: Database session
        check_relationship: When False (replying inside an existing
            conversation), only the plan gate is enforced; the
            applicant/shortlist relationship is not re-checked.

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

    # First check: does company have an active plan that includes messaging?
    # Plan gating goes through the entitlement service (single source of
    # truth), never an ad-hoc subscription query.
    company_user = await db.get(User, company_id)
    entitlements = (
        await get_entitlements(company_user, db) if company_user else PLAN_FEATURES["free"]
    )

    if not entitlements.is_active or not entitlements.candidate_messaging:
        return (
            False,
            MessagingDenial(
                "Your subscription has expired. Upgrade to send messages.",
                MESSAGING_ERROR_PLAN_REQUIRED,
            ),
        )

    if not check_relationship:
        return True, ""

    # Second check: policy-specific authorization
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
    2. Candidate user exists, has the candidate role, and is active
    """
    candidate_user = await db.get(User, candidate_id)
    if (
        not candidate_user
        or candidate_user.role != UserRole.candidate
        or not candidate_user.is_active
    ):
        return (
            False,
            MessagingDenial("This candidate is not available.", MESSAGING_ERROR_NOT_ELIGIBLE),
        )

    # Check if candidate has an application to any of company's jobs
    # in an active state (applied, shortlisted, interview)
    app = await db.scalar(
        select(Application)
        .join(JobPosting)
        .where(
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
        MessagingDenial(
            "You can message candidates who have applied to your jobs or whom you have shortlisted.",
            MESSAGING_ERROR_NOT_ELIGIBLE,
        ),
    )


async def _check_any_candidate_with_plan(
    company_id: UUID,
    candidate_id: UUID,
    db,
) -> tuple[bool, str]:
    """
    Check if company can message candidate under 'any_candidate_with_plan' policy.

    Allowed if:
    1. Company has an active subscription plan (already enforced by caller)
    2. Candidate exists and is active
    """
    # Check if candidate exists and is active
    candidate_user = await db.get(User, candidate_id)
    if (
        not candidate_user
        or candidate_user.role != UserRole.candidate
        or not candidate_user.is_active
    ):
        return (
            False,
            MessagingDenial("This candidate is not available.", MESSAGING_ERROR_NOT_ELIGIBLE),
        )

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

    is_participant = (user_role == UserRole.company and conv.company_id == user_id) or (
        user_role == UserRole.candidate and conv.candidate_id == user_id
    )

    if not is_participant:
        return False, "Conversation not found."

    return True, ""
