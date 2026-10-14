"""Authenticated file-serving endpoint.

All uploaded files are served through ``GET /files/{file_id}``.  Each
request verifies the caller's identity and checks authorization rules:

* **Owner**: always allowed.
* **Admin**: always allowed.
* **Company**: allowed for resumes, marksheets, and certificates ONLY if
  the candidate has applied to one of that company's jobs or has been
  shortlisted.  Any other candidate → 404 (not 403, to avoid confirming
  file existence).
* **Candidate profile photos**: allowed for authenticated company users
  who could view that candidate (i.e. the same visibility as the
  public-profile endpoint — any company user).
* **Company logos**: public-by-design, served from a separate prefix.
  Nothing else is public.

Local backend streams the file directly.  GCS backend redirects to a
short-lived signed URL (5 min).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from core.config import get_settings
from core.dependencies import CurrentUser, DbSession, get_optional_current_user
from models import (
    Application,
    FileCategory,
    FileRecord,
    JobPosting,
    User,
    UserRole,
)
from services.storage_service import (
    LOGO_PREFIX,
    generate_signed_url,
    get_local_file_path,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/files", tags=["files"])


async def _company_has_candidate_relationship(
    db, company_user_id: UUID, file_owner_id: UUID
) -> bool:
    """True if the candidate applied to (or was shortlisted for) any of the company's jobs."""
    result = await db.execute(
        select(Application.id)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .where(
            JobPosting.company_id == company_user_id,
            Application.candidate_id == file_owner_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _check_file_access(
    db, file_record: FileRecord, user: User
) -> None:
    """Raise HTTPException(404) if the user may NOT access this file.

    Returns None on success.  Uses 404 (not 403) for unauthorized access to
    avoid confirming file existence to attackers.
    """
    # Owner — always allowed.
    if user.id == file_record.owner_id:
        return

    # Admin — always allowed.
    if user.role == UserRole.admin:
        return

    # Company users have conditional access.
    if user.role == UserRole.company:
        # Photos: any authenticated company user can view candidate photos
        # (same visibility as the /candidates/{id}/public-profile endpoint).
        if file_record.category == FileCategory.photo:
            return

        # Documents (resumes, marksheets, certificates): only if the
        # candidate has applied/been-shortlisted to one of the company's jobs.
        if file_record.category == FileCategory.document:
            has_rel = await _company_has_candidate_relationship(
                db, user.id, file_record.owner_id
            )
            if has_rel:
                return

    # Logos: handled separately (public path).  If we get here for a logo
    # record, allow it — logos are public-by-design.
    if file_record.category == FileCategory.logo:
        return

    # Candidate trying to access another candidate's file — deny.
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{file_id}")
async def serve_file(file_id: UUID, user: CurrentUser, db: DbSession):
    """Serve an uploaded file with authorization checks.

    Local backend: returns the file directly.
    GCS backend: redirects to a 5-minute signed URL.
    """
    record = await db.get(FileRecord, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    await _check_file_access(db, record, user)

    if settings.storage_backend == "gcs":
        signed = generate_signed_url(record.storage_path, expiration_seconds=300)
        return RedirectResponse(url=signed, status_code=307)

    # Local backend — stream the file.
    path = get_local_file_path(record.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path=str(path),
        media_type=record.mime_type or "application/octet-stream",
        filename=record.original_filename,
    )


@router.get("/logo/{file_id}")
async def serve_logo(file_id: UUID, db: DbSession):
    """Serve company logos WITHOUT authentication.

    Company logos are public-by-design because they appear on unauthenticated
    job listing and company profile pages.  This is the ONLY public file
    endpoint.  All other files require authentication.
    """
    record = await db.get(FileRecord, file_id)
    if not record or record.category != FileCategory.logo:
        raise HTTPException(status_code=404, detail="Not found")

    if settings.storage_backend == "gcs":
        signed = generate_signed_url(record.storage_path, expiration_seconds=300)
        return RedirectResponse(url=signed, status_code=307)

    path = get_local_file_path(record.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path=str(path),
        media_type=record.mime_type or "application/octet-stream",
        filename=record.original_filename,
    )
