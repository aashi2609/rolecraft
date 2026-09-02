from uuid import UUID
import uuid as uuid_mod
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CompanyUser, CurrentUser, DbSession
from models import (
    CandidateProfile,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Project,
    Skill,
    User,
)
from schemas import (
    CandidateProfileOut,
    CandidateProfileUpdate,
    CandidatePublicProfileOut,
    CandidateSearchOut,
    CertificationIn,
    CertificationOut,
    EducationIn,
    EducationOut,
    ExperienceIn,
    ExperienceOut,
    ProjectIn,
    ProjectOut,
    SkillsUpdate,
)
from services.candidate_search_service import search_candidates
from services.profile_item_service import ProfileItemService

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Initialize profile item services
_education_service = ProfileItemService(Education, EducationIn, EducationIn, EducationOut)
_certification_service = ProfileItemService(Certification, CertificationIn, CertificationIn, CertificationOut)
_experience_service = ProfileItemService(Experience, ExperienceIn, ExperienceIn, ExperienceOut)
_project_service = ProfileItemService(Project, ProjectIn, ProjectIn, ProjectOut)


async def _load_profile(db, user_id: UUID) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.certifications),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.user),
        )
        .where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return profile


def _profile_meta(profile: CandidateProfile) -> tuple[Optional[str], dict[str, bool]]:
    links = profile.weblinks or {}
    display_name = links.get("display_name")
    prefs = links.get("notification_prefs") or {}
    if isinstance(prefs, dict):
        return display_name, {k: bool(v) for k, v in prefs.items()}
    return display_name, {}


def _to_out(profile: CandidateProfile) -> CandidateProfileOut:
    full_name, notification_prefs = _profile_meta(profile)
    return CandidateProfileOut(
        user_id=profile.user_id,
        email=profile.user.email if profile.user else None,
        full_name=full_name,
        photo_url=profile.photo_url,
        career_level=profile.career_level,
        dob=profile.dob,
        gender=profile.gender,
        marital_status=profile.marital_status,
        present_address=profile.present_address,
        permanent_address=profile.permanent_address,
        preferred_locations=profile.preferred_locations or [],
        preferred_sectors=profile.preferred_sectors or [],
        strengths=profile.strengths or [],
        weaknesses=profile.weaknesses or [],
        weblinks=profile.weblinks or {},
        notification_prefs=notification_prefs,
        annual_family_income=profile.annual_family_income,
        skills=[cs.skill.name for cs in profile.skills if cs.skill],
        education=[EducationOut.model_validate(e) for e in profile.education],
        certifications=[CertificationOut.model_validate(c) for c in profile.certifications],
        experience=[ExperienceOut.model_validate(e) for e in profile.experience],
        projects=[ProjectOut.model_validate(p) for p in profile.projects],
    )


def _public_weblinks(links: dict) -> dict:
    """Return only professional links suitable for employer-facing views."""
    allowed = {"linkedin", "github", "portfolio", "website", "behance", "dribbble"}
    out: dict = {}
    for key, value in (links or {}).items():
        if key in ("display_name", "notification_prefs"):
            continue
        if key.lower() in allowed and value:
            out[key] = value
    return out


def _to_public_out(profile: CandidateProfile) -> CandidatePublicProfileOut:
    full_name, _ = _profile_meta(profile)
    return CandidatePublicProfileOut(
        user_id=profile.user_id,
        full_name=full_name,
        photo_url=profile.photo_url,
        career_level=profile.career_level,
        skills=[cs.skill.name for cs in profile.skills if cs.skill],
        strengths=profile.strengths or [],
        weblinks=_public_weblinks(profile.weblinks or {}),
        education=[EducationOut.model_validate(e) for e in profile.education],
        certifications=[CertificationOut.model_validate(c) for c in profile.certifications],
        experience=[ExperienceOut.model_validate(e) for e in profile.experience],
        projects=[ProjectOut.model_validate(p) for p in profile.projects],
    )


@router.get("/me", response_model=CandidateProfileOut)
async def get_me(user: CandidateUser, db: DbSession):
    return _to_out(await _load_profile(db, user.id))


@router.put("/me", response_model=CandidateProfileOut)
async def update_me(body: CandidateProfileUpdate, user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    data = body.model_dump(exclude_unset=True)
    links = dict(profile.weblinks or {})
    if "full_name" in data:
        links["display_name"] = data.pop("full_name")
    if "notification_prefs" in data:
        links["notification_prefs"] = data.pop("notification_prefs")
    profile.weblinks = links
    for k, v in data.items():
        setattr(profile, k, v)
    await db.flush()
    return _to_out(await _load_profile(db, user.id))


# Education
@router.get("/me/education", response_model=list[EducationOut])
async def list_education(user: CandidateUser, db: DbSession):
    return await _education_service.list_items(db, user.id, _load_profile)


@router.post("/me/education", response_model=EducationOut)
async def add_education(body: EducationIn, user: CandidateUser, db: DbSession):
    return await _education_service.create_item(db, user.id, body)


@router.put("/me/education/{item_id}", response_model=EducationOut)
async def update_education(item_id: UUID, body: EducationIn, user: CandidateUser, db: DbSession):
    return await _education_service.update_item(db, item_id, user.id, body)


@router.delete("/me/education/{item_id}")
async def delete_education(item_id: UUID, user: CandidateUser, db: DbSession):
    return await _education_service.delete_item(db, item_id, user.id)


# Certifications
@router.get("/me/certifications", response_model=list[CertificationOut])
async def list_certs(user: CandidateUser, db: DbSession):
    return await _certification_service.list_items(db, user.id, _load_profile)


@router.post("/me/certifications", response_model=CertificationOut)
async def add_cert(body: CertificationIn, user: CandidateUser, db: DbSession):
    return await _certification_service.create_item(db, user.id, body)


@router.put("/me/certifications/{item_id}", response_model=CertificationOut)
async def update_cert(item_id: UUID, body: CertificationIn, user: CandidateUser, db: DbSession):
    return await _certification_service.update_item(db, item_id, user.id, body)


@router.delete("/me/certifications/{item_id}")
async def delete_cert(item_id: UUID, user: CandidateUser, db: DbSession):
    return await _certification_service.delete_item(db, item_id, user.id)


# Experience
@router.get("/me/experience", response_model=list[ExperienceOut])
async def list_exp(user: CandidateUser, db: DbSession):
    return await _experience_service.list_items(db, user.id, _load_profile)


@router.post("/me/experience", response_model=ExperienceOut)
async def add_exp(body: ExperienceIn, user: CandidateUser, db: DbSession):
    return await _experience_service.create_item(db, user.id, body)


@router.put("/me/experience/{item_id}", response_model=ExperienceOut)
async def update_exp(item_id: UUID, body: ExperienceIn, user: CandidateUser, db: DbSession):
    return await _experience_service.update_item(db, item_id, user.id, body)


@router.delete("/me/experience/{item_id}")
async def delete_exp(item_id: UUID, user: CandidateUser, db: DbSession):
    return await _experience_service.delete_item(db, item_id, user.id)


# Projects
@router.get("/me/projects", response_model=list[ProjectOut])
async def list_projects(user: CandidateUser, db: DbSession):
    return await _project_service.list_items(db, user.id, _load_profile)


@router.post("/me/projects", response_model=ProjectOut)
async def add_project(body: ProjectIn, user: CandidateUser, db: DbSession):
    return await _project_service.create_item(db, user.id, body)


@router.put("/me/projects/{item_id}", response_model=ProjectOut)
async def update_project(item_id: UUID, body: ProjectIn, user: CandidateUser, db: DbSession):
    return await _project_service.update_item(db, item_id, user.id, body)


@router.delete("/me/projects/{item_id}")
async def delete_project(item_id: UUID, user: CandidateUser, db: DbSession):
    return await _project_service.delete_item(db, item_id, user.id)


# Skills
@router.get("/me/skills")
async def get_skills(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return {"skills": [cs.skill.name for cs in profile.skills if cs.skill]}


@router.put("/me/skills")
async def put_skills(body: SkillsUpdate, user: CandidateUser, db: DbSession):
    unique_names: list[str] = []
    seen: set[str] = set()
    for raw in body.skills:
        name = raw.strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            unique_names.append(name)

    await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == user.id))
    await db.flush()

    linked: set[UUID] = set()
    for name in unique_names:
        skill = await db.scalar(select(Skill).where(Skill.name == name))
        if not skill:
            stmt = (
                insert(Skill)
                .values(id=uuid_mod.uuid4(), name=name)
                .on_conflict_do_nothing(index_elements=["name"])
            )
            await db.execute(stmt)
            skill = await db.scalar(select(Skill).where(Skill.name == name))
        if skill and skill.id not in linked:
            db.add(CandidateSkill(candidate_id=user.id, skill_id=skill.id))
            linked.add(skill.id)
    await db.flush()
    return {"skills": unique_names}


# ── Public Candidate Search ─────────────────────────────────────────────────────

@router.get("/search", response_model=list[CandidateSearchOut])
async def search_candidates_endpoint(
    db: DbSession,
    q: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    experience_min: Optional[int] = Query(None),
    experience_max: Optional[int] = Query(None),
    salary_min: Optional[int] = Query(None),
    salary_max: Optional[int] = Query(None),
    education: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Public candidate search endpoint with advanced filtering and pagination.
    This replaces the frontend SEED_CANDIDATES mock data.
    """
    candidates, _ = await search_candidates(
        db=db,
        q=q,
        location=location,
        skills=skills,
        experience_min=experience_min,
        experience_max=experience_max,
        salary_min=salary_min,
        salary_max=salary_max,
        education=education,
        title=title,
        page=page,
        page_size=page_size,
    )
    return candidates


@router.get("/{candidate_id}/public-profile", response_model=CandidatePublicProfileOut)
async def get_candidate_public_profile(candidate_id: UUID, user: CompanyUser, db: DbSession):
    """Employer-facing profile — no PII (address, income, DOB, family, etc.)."""
    return _to_public_out(await _load_profile(db, candidate_id))


@router.get("/{candidate_id}", response_model=CandidateProfileOut)
async def get_candidate_self(candidate_id: UUID, user: CandidateUser, db: DbSession):
    """Full profile — self-only. Other users must use /public-profile."""
    if user.id != candidate_id:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_out(await _load_profile(db, candidate_id))
