import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, exc
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CompanyUser, CurrentUser, DbSession, check_plan_limit
from core.security import decode_access_token
from core.ws_manager import ws_manager
from core.websocket_auth import authenticate_websocket_connection, handle_websocket_lifecycle
from models import Application, ApplicationStatus, Company, JobPosting, Resume, SavedJob, User
from schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate, JobOut
from services.resume_service import get_or_generate_resume

logger = logging.getLogger(__name__)

router = APIRouter(tags=["applications"])


async def _app_out(db, app: Application) -> ApplicationOut:
    job = await db.get(JobPosting, app.job_id)
    company = await db.get(Company, job.company_id) if job else None
    user = await db.get(User, app.candidate_id)
    # Use email prefix as display name (no dedicated name column exists yet)
    candidate_name = user.email.split("@")[0].replace(".", " ").title() if user else None
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
            Application.candidate_id == user.id, Application.job_id == body.job_id
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
                raise HTTPException(status_code=400, detail="Failed to generate resume and no fallback available")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.error("Failed to get or generate resume: %s", exc)
            raise HTTPException(status_code=500, detail="Resume generation failed")

    app = Application(candidate_id=user.id, job_id=body.job_id, resume_id=resume_id)
    db.add(app)
    try:
        await db.flush()
    except exc.IntegrityError:
        raise HTTPException(status_code=400, detail="You have already applied for this job")
    return await _app_out(db, app)


@router.get("/applications/me", response_model=list[ApplicationOut])
async def my_applications(user: CandidateUser, db: DbSession):
    apps = (
        await db.execute(
            select(Application)
            .where(Application.candidate_id == user.id)
            .order_by(Application.applied_at.desc())
        )
    ).scalars().all()
    return [await _app_out(db, a) for a in apps]


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
async def job_applications(job_id: UUID, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    apps = (
        await db.execute(
            select(Application).where(Application.job_id == job_id).order_by(Application.applied_at.desc())
        )
    ).scalars().all()
    return [await _app_out(db, a) for a in apps]


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
async def update_status(application_id: UUID, body: ApplicationStatusUpdate, user: CompanyUser, db: DbSession):
    app = await db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    job = await db.get(JobPosting, app.job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        app.status = ApplicationStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc
    await db.flush()

    result = await _app_out(db, app)

    # Broadcast real-time update to the candidate
    await ws_manager.send_to_user(app.candidate_id, {
        "type": "application_status_updated",
        "payload": {
            "id": str(result.id),
            "job_id": str(result.job_id),
            "status": result.status,
            "job_title": result.job_title,
            "company_name": result.company_name,
        },
    })

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
    existing = await db.get(SavedJob, {"candidate_id": user.id, "job_id": job_id})
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
        await db.execute(select(SavedJob).where(SavedJob.candidate_id == user.id))
    ).scalars().all()
    return {"job_ids": [str(r.job_id) for r in rows]}
