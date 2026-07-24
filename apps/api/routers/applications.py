from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CompanyUser, CurrentUser, DbSession
from models import Application, ApplicationStatus, Company, JobPosting, Resume, SavedJob
from schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate, JobOut

router = APIRouter(tags=["applications"])


async def _app_out(db, app: Application) -> ApplicationOut:
    job = await db.get(JobPosting, app.job_id)
    company = await db.get(Company, job.company_id) if job else None
    return ApplicationOut(
        id=app.id,
        candidate_id=app.candidate_id,
        job_id=app.job_id,
        resume_id=app.resume_id,
        status=app.status.value,
        applied_at=app.applied_at,
        job_title=job.title if job else None,
        company_name=company.name if company else None,
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
    await db.flush()
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
    return await _app_out(db, app)


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
