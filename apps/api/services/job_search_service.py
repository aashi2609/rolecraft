"""Job search service with composable filters."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from models import Application, ApplicationStatus, Company, JobPosting, JobStatus, JobType
from schemas import JobOut


def apply_status_filter(query, status: Optional[str], mine: bool):
    """Apply status filter."""
    if status:
        try:
            query = query.where(JobPosting.status == JobStatus(status))
        except ValueError:
            pass
    elif not mine:
        query = query.where(JobPosting.status == JobStatus.live)
    return query


def apply_title_filter(query, title: Optional[str]):
    """Apply title/description keyword filter."""
    if not title:
        return query
    return query.where(
        or_(
            JobPosting.title.ilike(f"%{title}%"),
            JobPosting.description.ilike(f"%{title}%"),
        )
    )


def apply_location_filter(query, location: Optional[str]):
    """Apply location filter."""
    if not location:
        return query
    return query.where(JobPosting.location.ilike(f"%{location}%"))


def apply_country_filter(query, country: Optional[str]):
    """Apply country filter."""
    if not country:
        return query
    return query.where(JobPosting.country.ilike(f"%{country}%"))


def apply_state_filter(query, state: Optional[str]):
    """Apply state filter."""
    if not state:
        return query
    return query.where(JobPosting.state.ilike(f"%{state}%"))


def apply_city_filter(query, city: Optional[str]):
    """Apply city filter."""
    if not city:
        return query
    return query.where(JobPosting.city.ilike(f"%{city}%"))


def apply_employment_type_filter(query, employment_type: Optional[str]):
    """Apply employment type filter."""
    if not employment_type:
        return query
    return query.where(JobPosting.employment_type == employment_type)


def apply_experience_range_filter(query, experience_range: Optional[str]):
    """Apply experience range filter."""
    if not experience_range:
        return query
    return query.where(JobPosting.experience_range.ilike(f"%{experience_range}%"))


def apply_job_type_filter(query, job_type: Optional[str]):
    """Apply remote/hybrid/onsite filter."""
    if not job_type:
        return query
    try:
        return query.where(JobPosting.job_type == JobType(job_type.lower()))
    except ValueError:
        return query


def apply_vertical_filter(query, vertical: Optional[str]):
    """Apply vertical/department filter."""
    if not vertical:
        return query
    return query.where(JobPosting.department.ilike(f"%{vertical}%"))


def apply_job_role_filter(query, job_role: Optional[str]):
    """Apply job role filter."""
    if not job_role:
        return query
    return query.where(JobPosting.job_role.ilike(f"%{job_role}%"))


def apply_job_level_filter(query, job_level: Optional[str]):
    """Apply job level filter."""
    if not job_level:
        return query
    return query.where(JobPosting.job_level.ilike(f"%{job_level}%"))


def apply_salary_min_filter(query, salary_min: Optional[int]):
    """Apply minimum salary filter."""
    if salary_min is None:
        return query
    return query.where(JobPosting.max_salary >= salary_min)


def apply_salary_max_filter(query, salary_max: Optional[int]):
    """Apply maximum salary filter."""
    if salary_max is None:
        return query
    return query.where(JobPosting.min_salary <= salary_max)


def apply_exclude_country_filter(query, exclude_country: Optional[str]):
    """Apply negative country filter (exclude specified countries)."""
    if not exclude_country:
        return query
    for val in exclude_country.split(","):
        val = val.strip()
        if val:
            query = query.where(~JobPosting.country.ilike(f"%{val}%"))
    return query


def apply_exclude_state_filter(query, exclude_state: Optional[str]):
    """Apply negative state filter (exclude specified states)."""
    if not exclude_state:
        return query
    for val in exclude_state.split(","):
        val = val.strip()
        if val:
            query = query.where(~JobPosting.state.ilike(f"%{val}%"))
    return query


def apply_exclude_city_filter(query, exclude_city: Optional[str]):
    """Apply negative city filter (exclude specified cities)."""
    if not exclude_city:
        return query
    for val in exclude_city.split(","):
        val = val.strip()
        if val:
            query = query.where(~JobPosting.city.ilike(f"%{val}%"))
    return query


async def enrich_job(db, job: JobPosting) -> JobOut:
    """Enrich job with company name and application pipeline counts.

    matched     = total applications for this job (pipeline size)
    shortlisted = applications with status ApplicationStatus.shortlisted

    These are real aggregates from `applications`, not stubs. FitmentResult
    rankings are separate (GET /jobs/{id}/candidates) and are not included here.
    """
    from sqlalchemy import func

    try:
        company = await db.get(Company, job.company_id)
    except Exception:
        company = None

    matched = await db.scalar(
        select(func.count()).select_from(Application).where(Application.job_id == job.id)
    ) or 0
    shortlisted = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.job_id == job.id,
            Application.status == ApplicationStatus.shortlisted,
        )
    ) or 0
    data = JobOut.model_validate(job)
    data.company_name = company.name if company else None
    # Enum values already coerced by JobOut validators; keep explicit .value for clarity
    if job.job_type is not None:
        data.job_type = job.job_type.value
    data.status = job.status.value if job.status else "draft"
    data.matched = int(matched)
    data.shortlisted = int(shortlisted)
    return data


async def search_jobs(
    db,
    title: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    exclude_country: Optional[str] = None,
    exclude_state: Optional[str] = None,
    exclude_city: Optional[str] = None,
    employment_type: Optional[str] = None,
    job_type: Optional[str] = None,
    experience_range: Optional[str] = None,
    vertical: Optional[str] = None,
    job_role: Optional[str] = None,
    job_level: Optional[str] = None,
    status: Optional[str] = None,
    mine: bool = False,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
) -> list[JobOut]:
    """
    Search jobs with advanced filtering.
    Returns list of enriched JobOut objects.
    """
    # Build base query with company preloaded
    query = select(JobPosting).options(selectinload(JobPosting.company))
    
    # Apply filters in sequence
    query = apply_status_filter(query, status, mine)
    query = apply_title_filter(query, title)
    query = apply_location_filter(query, location)
    query = apply_country_filter(query, country)
    query = apply_state_filter(query, state)
    query = apply_city_filter(query, city)
    query = apply_employment_type_filter(query, employment_type)
    query = apply_job_type_filter(query, job_type)
    query = apply_experience_range_filter(query, experience_range)
    query = apply_vertical_filter(query, vertical)
    query = apply_job_role_filter(query, job_role)
    query = apply_job_level_filter(query, job_level)
    query = apply_salary_min_filter(query, salary_min)
    query = apply_salary_max_filter(query, salary_max)
    query = apply_exclude_country_filter(query, exclude_country)
    query = apply_exclude_state_filter(query, exclude_state)
    query = apply_exclude_city_filter(query, exclude_city)
    
    # Order by creation date
    query = query.order_by(JobPosting.created_at.desc())
    
    # Execute query
    jobs = (await db.execute(query)).scalars().all()
    
    # Enrich results
    out = []
    for job in jobs:
        out.append(await enrich_job(db, job))
    return out
