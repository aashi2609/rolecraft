from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from core.dependencies import CompanyUser, DbSession, check_plan_limit
from models import Application, ApplicationStatus, Company, JobPosting, JobStatus, JobType, UserRole
from schemas import FitmentCandidateOut, JobCreate, JobOut, JobStatusUpdate, JobUpdate
from services.fitment_service import compute_fitment

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_type(raw: str | None) -> JobType | None:
    if not raw:
        return None
    key = raw.lower().replace("-", "").replace(" ", "")
    mapping = {"onsite": JobType.onsite, "remote": JobType.remote, "hybrid": JobType.hybrid}
    return mapping.get(key)


async def _enrich(db, job: JobPosting) -> JobOut:
    company = await db.get(Company, job.company_id)
    matched = await db.scalar(
        select(func.count()).select_from(Application).where(Application.job_id == job.id)
    ) or 0
    shortlisted = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.job_id == job.id, Application.status == ApplicationStatus.shortlisted)
    ) or 0
    data = JobOut.model_validate(job)
    data.company_name = company.name if company else None
    data.job_type = job.job_type.value if job.job_type else None
    data.status = job.status.value
    data.matched = matched
    data.shortlisted = shortlisted
    return data


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, user: CompanyUser, db: DbSession):
    status = JobStatus(body.status) if body.status in JobStatus.__members__ else JobStatus.draft
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
    return await _enrich(db, job)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    db: DbSession,
    title: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    experience_range: str | None = None,
    vertical: str | None = None,
    status: str | None = None,
    mine: bool = False,
    salary_min: int | None = Query(None),
):
    # Public browse endpoint (no auth). Company "my jobs" is GET /jobs/mine.
    q = select(JobPosting).options(selectinload(JobPosting.company))
    if status:
        try:
            q = q.where(JobPosting.status == JobStatus(status))
        except ValueError:
            pass
    elif not mine:
        q = q.where(JobPosting.status == JobStatus.live)

    if title:
        q = q.where(
            or_(
                JobPosting.title.ilike(f"%{title}%"),
                JobPosting.description.ilike(f"%{title}%"),
            )
        )
    if location:
        q = q.where(JobPosting.location.ilike(f"%{location}%"))
    if employment_type:
        q = q.where(JobPosting.employment_type == employment_type)
    if experience_range:
        q = q.where(JobPosting.experience_range.ilike(f"%{experience_range}%"))
    if vertical:
        q = q.where(JobPosting.department.ilike(f"%{vertical}%"))
    if salary_min is not None:
        q = q.where(JobPosting.max_salary >= salary_min)

    q = q.order_by(JobPosting.created_at.desc())
    jobs = (await db.execute(q)).scalars().all()

    # If mine=true, filter to caller's company jobs when authenticated as company
    # (optional header — list endpoint also used publicly for browse)
    out = []
    for job in jobs:
        out.append(await _enrich(db, job))
    return out


@router.get("/mine", response_model=list[JobOut])
async def my_jobs(user: CompanyUser, db: DbSession):
    jobs = (
        await db.execute(
            select(JobPosting)
            .where(JobPosting.company_id == user.id)
            .order_by(JobPosting.created_at.desc())
        )
    ).scalars().all()
    return [await _enrich(db, j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return await _enrich(db, job)


@router.put("/{job_id}", response_model=JobOut)
async def update_job(job_id: UUID, body: JobUpdate, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    data = body.model_dump(exclude_unset=True)
    if "job_type" in data:
        data["job_type"] = _job_type(data["job_type"])
    for k, v in data.items():
        setattr(job, k, v)
    await db.flush()
    return await _enrich(db, job)


@router.patch("/{job_id}/status", response_model=JobOut)
async def patch_status(job_id: UUID, body: JobStatusUpdate, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        job.status = JobStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc
    await db.flush()
    return await _enrich(db, job)


@router.get("/{job_id}/candidates", response_model=list[FitmentCandidateOut])
async def ranked_candidates(job_id: UUID, user: CompanyUser, db: DbSession):
    job = await db.get(JobPosting, job_id)
    if not job or job.company_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    results = await compute_fitment(db, job)
    out: list[FitmentCandidateOut] = []
    for fr in results:
        from models import CandidateProfile, CandidateSkill

        profile = (
            await db.execute(
                select(CandidateProfile)
                .options(selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill), selectinload(CandidateProfile.user))
                .where(CandidateProfile.user_id == fr.candidate_id)
            )
        ).scalar_one_or_none()
        skills = [cs.skill.name for cs in (profile.skills if profile else []) if cs.skill]
        email = profile.user.email if profile and profile.user else None
        name = (email.split("@")[0].replace(".", " ").title() if email else "Candidate")
        out.append(
            FitmentCandidateOut(
                candidate_id=fr.candidate_id,
                name=name,
                title=(profile.preferred_sectors or [None])[0] if profile else None,
                score=fr.score,
                rationale=fr.rationale,
                skills=skills,
                location=(profile.preferred_locations or [None])[0] if profile else None,
            )
        )
    out.sort(key=lambda x: x.score, reverse=True)
    return out
