import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket
from sqlalchemy import exc, select

from core.dependencies import (
    CandidateUser,
    CompanyUser,
    DbSession,
    check_plan_limit,
)
from core.websocket_auth import (
    authenticate_websocket_connection,
    handle_websocket_lifecycle,
)
from core.enum_utils import coerce_enum
from core.ws_manager import ws_manager
from models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Company,
    JobPosting,
    Resume,
    SavedJob,
    User,
)
from schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
)
from services.resume_service import get_or_generate_resume

logger = logging.getLogger(__name__)

router = APIRouter(tags=["applications"])


async def _app_out(
    app: Application,
    job: JobPosting = None,
    company: Company = None,
    user: User = None,
    profile: CandidateProfile = None,
    resume: Resume = None,
) -> ApplicationOut:
    """
    Serialize application to ApplicationOut.
    All supporting entities should be pre-loaded to avoid N+1 queries.
    
    Args:
        app: Application model instance
        job: Pre-loaded JobPosting (from eager load or batch)
        company: Pre-loaded Company (from batch)
        user: Pre-loaded User (from batch)
        profile: Pre-loaded CandidateProfile (from batch)
        resume: Pre-loaded Resume (from eager load or batch)
    """
    # Try to get candidate name from profile weblinks (resume parsing stores it here)
    candidate_name = None
    if user:
        if profile and profile.weblinks:
            # Check for name variations in weblinks (from resume parsing or profile)
            candidate_name = (
                profile.weblinks.get('full_name') or 
                profile.weblinks.get('name') or 
                profile.weblinks.get('display_name') or
                profile.weblinks.get('linkedin')
            )
        
        # If still no name, try to get from resume metadata (if available)
        if not candidate_name and resume:
            # Resume might have parsed candidate name in metadata
            pass  # Resume model doesn't have candidate_name field currently
        
        # Final fallback: use email prefix and clean it up
        if not candidate_name:
            email_prefix = user.email.split("@")[0]
            candidate_name = email_prefix.replace(".", " ").replace("_", " ").replace("-", " ").title()
    
    return ApplicationOut(
        id=app.id,
        candidate_id=app.candidate_id,
        job_id=app.job_id,
        resume_id=app.resume_id,
        status=app.status.value,
        applied_at=app.applied_at,
        job_title=job.title if job else None,
        company_name=company.name if company else None,
        candidate_name=candidate_name,
    )


@router.post("/applications", response_model=ApplicationOut)
async def apply(body: ApplicationCreate, user: CandidateUser, db: DbSession):
    job = await db.get(JobPosting, body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = await db.scalar(
        select(Application).where(
            Application.candidate_id == user.id,
            Application.job_id == body.job_id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")

    resume_id = body.resume_id
    if resume_id:
        resume = await db.get(Resume, resume_id)
        if not resume or resume.candidate_id != user.id:
            raise HTTPException(status_code=400, detail="Invalid resume")
    else:
        # Dynamically generate a tailored resume for this job
        await check_plan_limit(user, db, "resume_verticals", extra=1)

        target_vertical = job.title or "Job Application"
        try:
            resume_id = await get_or_generate_resume(
                db, user.id, target_vertical, user.email
            )
            if not resume_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Failed to generate resume and no fallback available"
                    ),
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.error("Failed to get or generate resume: %s", exc)
            raise HTTPException(
                status_code=500, detail="Resume generation failed"
            )

    app = Application(
        candidate_id=user.id, job_id=body.job_id, resume_id=resume_id
    )
    db.add(app)
    try:
        await db.flush()
    except exc.IntegrityError:
        raise HTTPException(
            status_code=400, detail="You have already applied for this job"
        )
    
    # Refresh to load relationships and convert to output
    await db.refresh(app)
    return await _app_out(
        app,
        job=job,
        company=await db.get(Company, job.company_id) if job else None,
        user=user,
        profile=await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id)),
        resume=await db.get(Resume, app.resume_id) if app.resume_id else None,
    )


@router.get("/applications/me", response_model=list[ApplicationOut])
async def my_applications(user: CandidateUser, db: DbSession):
    """
    Get candidate's applications with optimized batch loading.
    
    Fetches all related data (jobs, companies, profiles) in fixed 3 queries:
    1. Applications (with eager-loaded Job.Company and Resume)
    2. CandidateProfiles for candidates
    3. Users for candidates
    
    Query count is constant regardless of result set size.
    """
    # Query 1: Fetch applications with eager-loaded relationships
    apps = (
        (
            await db.execute(
                select(Application)
                .options(
                    selectinload(Application.job).selectinload(JobPosting.company),
                    selectinload(Application.resume),
                )
                .where(Application.candidate_id == user.id)
                .order_by(Application.applied_at.desc())
            )
        )
        .scalars()
        .unique()
        .all()
    )
    
    if not apps:
        return []
    
    # Extract candidate IDs (all should be same user, but batch for completeness)
    candidate_ids = list(set([a.candidate_id for a in apps]))
    
    # Query 2: Batch-load candidate profiles
    profiles_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id.in_(candidate_ids))
    )
    profiles_dict = {p.user_id: p for p in profiles_result.scalars().all()}
    
    # Query 3: Batch-load users
    users_result = await db.execute(
        select(User).where(User.id.in_(candidate_ids))
    )
    users_dict = {u.id: u for u in users_result.scalars().all()}
    
    # Serialize with pre-loaded data (no additional queries)
    result = []
    for app in apps:
        profile = profiles_dict.get(app.candidate_id)
        app_user = users_dict.get(app.candidate_id)
        
        result.append(await _app_out(
            app,
            job=app.job,
            company=app.job.company if app.job else None,
            user=app_user,
            profile=profile,
            resume=app.resume,
        ))
    
    return result


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
async def job_applications(job_id: UUID, user: CompanyUser, db: DbSession):
    """
    Get applications for a specific job with optimized batch loading.
    
    Fetches all related data in fixed 3 queries:
    1. Applications (with eager-loaded Job and Resume)
    2. CandidateProfiles
    3. Users
    """
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Query 1: Fetch applications with eager-loaded relationships
    apps = (
        (
            await db.execute(
                select(Application)
                .options(
                    selectinload(Application.job),
                    selectinload(Application.resume),
                )
                .where(Application.job_id == job_id)
                .order_by(Application.applied_at.desc())
            )
        )
        .scalars()
        .unique()
        .all()
    )
    
    if not apps:
        return []
    
    # Extract candidate IDs for batch loading
    candidate_ids = list(set([a.candidate_id for a in apps]))
    
    # Query 2: Batch-load candidate profiles
    profiles_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id.in_(candidate_ids))
    )
    profiles_dict = {p.user_id: p for p in profiles_result.scalars().all()}
    
    # Query 3: Batch-load users
    users_result = await db.execute(
        select(User).where(User.id.in_(candidate_ids))
    )
    users_dict = {u.id: u for u in users_result.scalars().all()}
    
    # Serialize with pre-loaded data
    result = []
    for app in apps:
        profile = profiles_dict.get(app.candidate_id)
        app_user = users_dict.get(app.candidate_id)
        
        result.append(await _app_out(
            app,
            job=app.job or job,  # Use job from app if present, else the queried job
            company=job.company,  # Use the company from the job
            user=app_user,
            profile=profile,
            resume=app.resume,
        ))
    
    return result


@router.patch(
    "/applications/{application_id}/status", response_model=ApplicationOut
)
async def update_status(
    application_id: UUID,
    body: ApplicationStatusUpdate,
    user: CompanyUser,
    db: DbSession,
):
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    job = await db.get(JobPosting, app.job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    app.status = coerce_enum(ApplicationStatus, body.status, "status", allow_none=False)
    await db.flush()

    # Batch load related data for serialization
    app_user = await db.get(User, app.candidate_id)
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == app.candidate_id))
    company = await db.get(Company, job.company_id) if job else None
    
    result = await _app_out(
        app,
        job=job,
        company=company,
        user=app_user,
        profile=profile,
        resume=None,  # Not needed for status update response
    )

    # Broadcast real-time update to the candidate
    await ws_manager.send_to_user(
        app.candidate_id,
        {
            "type": "application_status_updated",
            "payload": {
                "id": str(result.id),
                "job_id": str(result.job_id),
                "status": result.status,
                "job_title": result.job_title,
                "company_name": result.company_name,
            },
        },
    )

    return result


# ── WebSocket: real-time application events ────────────────────────────
@router.websocket("/ws/applications")
async def ws_applications(websocket: WebSocket):
    """Authenticated WebSocket endpoint for real-time application updates.

    The client must send a JSON message with {"token": "<jwt>"} immediately
    after connecting.  The server validates the token, registers the
    connection, and keeps it alive.  Events are pushed as JSON objects with
    a "type" field (e.g. "application_status_updated").
    """
    user_id = await authenticate_websocket_connection(websocket)
    if user_id is None:
        return

    await handle_websocket_lifecycle(websocket, user_id)


# Saved jobs
@router.post("/saved-jobs/{job_id}")
async def save_job(job_id: UUID, user: CandidateUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = await db.get(
        SavedJob, {"candidate_id": user.id, "job_id": job_id}
    )
    if not existing:
        db.add(SavedJob(candidate_id=user.id, job_id=job_id))
        await db.flush()
    return {"ok": True}


@router.delete("/saved-jobs/{job_id}")
async def unsave_job(job_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(SavedJob, {"candidate_id": user.id, "job_id": job_id})
    if row:
        await db.delete(row)
    return {"ok": True}


@router.get("/saved-jobs/me")
async def list_saved(user: CandidateUser, db: DbSession):
    rows = (
        (
            await db.execute(
                select(SavedJob).where(SavedJob.candidate_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    return {"job_ids": [str(r.job_id) for r in rows]}
