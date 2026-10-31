from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy import select

from core.dependencies import CandidateUser, CompanyUser, DbSession, check_plan_limit, get_optional_current_user
from core.enum_utils import coerce_enum
from core.rate_limit import RATE_LIMITS, get_user_key, limiter
from models import EmploymentType, HiddenJob, JobPosting, JobStatus, JobType, User, UserRole
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
    return coerce_enum(JobType, raw, "job_type")


@router.post("/parse-jd", response_model=JobParsedJDOut)
@limiter.limit(RATE_LIMITS["groq_burst_user"], key_func=get_user_key)
async def parse_jd(
    request: Request,
    response: Response,
    user: CompanyUser,
    file: UploadFile = File(...),
):
    """Upload a JD (PDF or TXT) and extract fields for the post-job form."""
    from core.upload_limits import sanitize_filename, validate_upload

    raw_filename = file.filename or "jd.pdf"
    safe_filename = sanitize_filename(raw_filename)
    lower = safe_filename.lower()
    if lower.endswith(".txt"):
        data = await file.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    else:
        data, _, _ = await validate_upload(file, "document")
        if not (data.startswith(b"%PDF") or lower.endswith(".pdf")):
            raise HTTPException(
                status_code=400, detail="Upload a PDF or TXT job description"
            )

    parsed = await parse_job_description(data, filename=safe_filename)
    return JobParsedJDOut.model_validate(parsed)


from typing import Annotated
from core.dependencies import require_role

@router.post("", response_model=JobOut)
async def create_job(
    body: JobCreate, 
    user: Annotated[User, Depends(require_role(UserRole.company, UserRole.admin))], 
    db: DbSession
):
    # Convert status to enum
    status = coerce_enum(JobStatus, body.status, "status") or JobStatus.draft

    if user.role == UserRole.admin:
        if not body.company_id:
            raise HTTPException(status_code=400, detail="company_id is required for admins")
        company_id = body.company_id
        company_exists = await db.get(User, company_id)
        if not company_exists or company_exists.role != UserRole.company:
            raise HTTPException(status_code=400, detail="Company not found")
    else:
        if body.company_id and body.company_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot create job for another company")
        company_id = user.id

    if status in (JobStatus.live, JobStatus.draft):
        await check_plan_limit(user, db, "job_postings")

    job = JobPosting(
        company_id=company_id,
        title=body.title,
        department=body.department,
        employment_type=(coerce_enum(EmploymentType, body.employment_type, "employment_type").value if body.employment_type else None),
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
    user: User | None = Depends(get_optional_current_user),
    exclude_hidden: bool = True,
):
    """Public browse endpoint (no auth required). Company 'my jobs' is GET /jobs/mine.
    If authenticated as candidate and exclude_hidden is True, hidden jobs are excluded.
    """
    exclude_ids: list[UUID] | None = None
    if user and user.role == UserRole.candidate and exclude_hidden:
        hidden_ids = await db.scalars(
            select(HiddenJob.job_id).where(HiddenJob.candidate_id == user.id)
        )
        exclude_ids = list(hidden_ids.all())

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
        exclude_ids=exclude_ids,
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


@router.get("/hidden")
async def list_hidden_jobs(user: CandidateUser, db: DbSession):
    hidden = await db.scalars(
        select(HiddenJob.job_id).where(HiddenJob.candidate_id == user.id)
    )
    return {"job_ids": [str(j) for j in hidden.all()]}


@router.get("/{job_id:uuid}", response_model=JobOut)
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


@router.put("/{job_id:uuid}", response_model=JobOut)
@router.patch("/{job_id:uuid}", response_model=JobOut)
async def update_job(job_id: UUID, body: JobUpdate, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "job_type":
            job.job_type = coerce_enum(JobType, v, "job_type")
        elif k == "status":
            job.status = coerce_enum(JobStatus, v, "status", allow_none=False)
        elif k == "employment_type":
            emp = coerce_enum(EmploymentType, v, "employment_type")
            job.employment_type = emp.value if emp else None
        else:
            setattr(job, k, v)
    await db.flush()
    await refresh_job_embedding(db, job)
    return await enrich_job(db, job)


@router.patch("/{job_id:uuid}/status", response_model=JobOut)
async def patch_status(
    job_id: UUID, body: JobStatusUpdate, user: CompanyUser, db: DbSession
):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    job.status = coerce_enum(JobStatus, body.status, "status", allow_none=False)
    await db.flush()
    return await enrich_job(db, job)


@router.get("/{job_id:uuid}/candidates", response_model=list[FitmentCandidateOut])
async def ranked_candidates(job_id: UUID, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return await ranked_candidates_for_job(db, job)


@router.post("/{job_id:uuid}/hide")
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


@router.delete("/{job_id:uuid}/hide")
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
