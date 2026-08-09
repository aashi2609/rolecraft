import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, exc
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CompanyUser, CurrentUser, DbSession
from core.security import decode_access_token
from core.ws_manager import ws_manager
from models import Application, ApplicationStatus, Company, JobPosting, Resume, SavedJob, User
from schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate, JobOut

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
        resume = await db.scalar(
            select(Resume)
            .where(Resume.candidate_id == user.id)
            .order_by(Resume.is_default.desc(), Resume.created_at.desc())
        )
        resume_id = resume.id if resume else None

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
    await websocket.accept()
    # Wait for the client to send their auth token
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
    except Exception:
        await websocket.close(code=4001, reason="Auth timeout")
        return

    token = auth_msg.get("token")
    if not token:
        await websocket.close(code=4002, reason="Missing token")
        return

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        await websocket.close(code=4003, reason="Invalid token")
        return

    await ws_manager.connect(user_id, websocket)
    try:
        # Keep the connection alive — listen for pings or client messages
        while True:
            data = await websocket.receive_json()
            # Handle client-side ping to keep the connection alive
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error for user=%s: %s", user_id, exc)
    finally:
        await ws_manager.disconnect(user_id, websocket)


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
