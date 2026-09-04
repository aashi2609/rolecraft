from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select

from core.dependencies import CandidateUser, CompanyUser, DbSession, check_plan_limit, get_optional_current_user
from models import HiddenJob, JobPosting, JobStatus, JobType, User, UserRole
from schemas import (
    FitmentCandidateOut,
    JobCreate,
    JobOut,
    JobParsedJDOut,
    JobStatusUpdate,
    JobUpdate,
)
from services.embedding_service import refresh_job_embedding
from services.fitment_service import ranked_candidates_for_job
from services.jd_parse_service import parse_job_description
from services.job_search_service import enrich_job, search_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_type(raw: str | None) -> JobType | None:
    if not raw:
        return None
    key = raw.lower().replace("-", "").replace(" ", "")
    mapping = {
        "onsite": JobType.onsite,
        "remote": JobType.remote,
        "hybrid": JobType.hybrid,
    }
    return mapping.get(key)


@router.post("/parse-jd", response_model=JobParsedJDOut)
async def parse_jd(user: CompanyUser, file: UploadFile = File(...)):
    """Upload a JD (PDF or TXT) and extract fields for the post-job form."""
    from core.upload_limits import validate_upload

    filename = file.filename or "jd.pdf"
    lower = filename.lower()
    if lower.endswith(".txt"):
        data = await file.read()
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    else:
        data, _, _ = await validate_upload(file, "document")
        if not (data.startswith(b"%PDF") or lower.endswith(".pdf")):
            raise HTTPException(
                status_code=400, detail="Upload a PDF or TXT job description"
            )

    parsed = await parse_job_description(data, filename=filename)
    return JobParsedJDOut.model_validate(parsed)


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, user: CompanyUser, db: DbSession):
    # Convert string status to enum
    if body.status and body.status in JobStatus.__members__:
        status = JobStatus(body.status)
    else:
        status = JobStatus.draft

    if status in (JobStatus.live, JobStatus.draft):
        await check_plan_limit(user, db, "job_postings")

    job = JobPosting(
        company_id=user.id,
        title=body.title,
        department=body.department,
        employment_type=body.employment_type,
        experience_range=body.experience_range,
        min_salary=body.min_salary,
        max_salary=body.max_salary,
        salary_unit=body.salary_unit,
        location=body.location,
        country=body.country,
        state=body.state,
        city=body.city,
        job_role=body.job_role,
        job_level=body.job_level,
        job_type=_job_type(body.job_type),
        required_skills=body.required_skills,
        num_openings=body.num_openings,
        application_deadline=body.application_deadline,
        description=body.description,
        responsibilities=body.responsibilities,
        requirements=body.requirements,
        benefits=body.benefits,
        status=status,
    )
    db.add(job)
    await db.flush()
    await refresh_job_embedding(db, job)
    return await enrich_job(db, job)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    db: DbSession,
    title: str | None = None,
    location: str | None = None,
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    exclude_country: str | None = Query(
        None, description="Comma-separated countries to exclude"
    ),
    exclude_state: str | None = Query(
        None, description="Comma-separated states to exclude"
    ),
    exclude_city: str | None = Query(
        None, description="Comma-separated cities to exclude"
    ),
    employment_type: str | None = None,
    job_type: str | None = None,
    experience_range: str | None = None,
    vertical: str | None = None,
    job_role: str | None = None,
    job_level: str | None = None,
    status: str | None = None,
    mine: bool = False,
    salary_min: int | None = Query(None),
    salary_max: int | None = Query(None),
):
    """Public browse endpoint (no auth). Company 'my jobs' is GET /jobs/mine."""
    return await search_jobs(
        db=db,
        title=title,
        location=location,
        country=country,
        state=state,
        city=city,
        exclude_country=exclude_country,
        exclude_state=exclude_state,
        exclude_city=exclude_city,
        employment_type=employment_type,
        job_type=job_type,
        experience_range=experience_range,
        vertical=vertical,
        job_role=job_role,
        job_level=job_level,
        status=status,
        mine=mine,
        salary_min=salary_min,
        salary_max=salary_max,
    )


@router.get("/mine", response_model=list[JobOut])
async def my_jobs(user: CompanyUser, db: DbSession):
    jobs = (
        (
            await db.execute(
                select(JobPosting)
                .where(JobPosting.company_id == user.id)
                .order_by(JobPosting.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [await enrich_job(db, j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID, db: DbSession, user: User | None = Depends(get_optional_current_user)
):
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.live:
        is_owner = (
            user is not None
            and user.role == UserRole.company
            and job.company_id == user.id
        )
        if not is_owner:
            raise HTTPException(status_code=404, detail="Job not found")
    return await enrich_job(db, job)


@router.put("/{job_id}", response_model=JobOut)
async def update_job(job_id: UUID, body: JobUpdate, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "job_type" in data:
        data["job_type"] = _job_type(data["job_type"])
    for k, v in data.items():
        setattr(job, k, v)
    await db.flush()
    await refresh_job_embedding(db, job)
    return await enrich_job(db, job)


@router.patch("/{job_id}/status", response_model=JobOut)
async def patch_status(
    job_id: UUID, body: JobStatusUpdate, user: CompanyUser, db: DbSession
):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        job.status = JobStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc
    await db.flush()
    return await enrich_job(db, job)


@router.get("/{job_id}/candidates", response_model=list[FitmentCandidateOut])
async def ranked_candidates(job_id: UUID, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return await ranked_candidates_for_job(db, job)





@router.post("/{job_id}/hide")
async def hide_job(job_id: UUID, user: CandidateUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    hidden = await db.scalar(
        select(HiddenJob).where(
            HiddenJob.job_id == job_id, HiddenJob.candidate_id == user.id
        )
    )
    if not hidden:
        db.add(HiddenJob(candidate_id=user.id, job_id=job_id))
        await db.flush()
    return {"status": "ok"}


@router.delete("/{job_id}/hide")
async def unhide_job(job_id: UUID, user: CandidateUser, db: DbSession):
    hidden = await db.scalar(
        select(HiddenJob).where(
            HiddenJob.job_id == job_id, HiddenJob.candidate_id == user.id
        )
    )
    if hidden:
        await db.delete(hidden)
        await db.flush()
    return {"status": "ok"}
