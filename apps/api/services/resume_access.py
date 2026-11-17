"""Step C: single authorization rule for company access to a candidate's resume.

A company may view EXACTLY the resume the candidate submitted on an
application to one of that company's jobs — not the candidate's other
resumes, not their current default.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Application, JobPosting

logger = logging.getLogger(__name__)


async def can_company_view_resume(
    company_id: UUID, resume_id: UUID, db: AsyncSession
) -> bool:
    """True only if an application exists whose resume_id is THIS resume
    and whose job belongs to THIS company."""
    app = await db.scalar(
        select(Application.id)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(
            Application.resume_id == resume_id,
            JobPosting.company_id == company_id,
        )
        .limit(1)
    )
    return app is not None


async def get_resume_application(
    company_id: UUID, resume_id: UUID, db: AsyncSession
):
    """Return the matching Application (for audit logging) or None."""
    return await db.scalar(
        select(Application)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(
            Application.resume_id == resume_id,
            JobPosting.company_id == company_id,
        )
        .limit(1)
    )


def log_resume_view(company_id: UUID, resume_id: UUID, application_id) -> None:
    """Audit a company resume view. No resume content is ever logged.

    NOTE: no dedicated audit table exists and new models are out of scope
    for this step — emitted as a structured log line until a product
    decision on the audit store is made (see Step C report).
    """
    logger.info(
        "resume_view company_id=%s resume_id=%s application_id=%s",
        company_id,
        resume_id,
        application_id,
    )
