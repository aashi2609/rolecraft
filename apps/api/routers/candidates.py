from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CurrentUser, DbSession
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

router = APIRouter(prefix="/candidates", tags=["candidates"])


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


def _to_out(profile: CandidateProfile) -> CandidateProfileOut:
    return CandidateProfileOut(
        user_id=profile.user_id,
        email=profile.user.email if profile.user else None,
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
        annual_family_income=profile.annual_family_income,
        skills=[cs.skill.name for cs in profile.skills if cs.skill],
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
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)
    await db.flush()
    return _to_out(await _load_profile(db, user.id))


# Education
@router.get("/me/education", response_model=list[EducationOut])
async def list_education(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [EducationOut.model_validate(e) for e in profile.education]


@router.post("/me/education", response_model=EducationOut)
async def add_education(body: EducationIn, user: CandidateUser, db: DbSession):
    row = Education(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return EducationOut.model_validate(row)


@router.put("/me/education/{item_id}", response_model=EducationOut)
async def update_education(item_id: UUID, body: EducationIn, user: CandidateUser, db: DbSession):
    row = await db.get(Education, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return EducationOut.model_validate(row)


@router.delete("/me/education/{item_id}")
async def delete_education(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Education, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Certifications
@router.get("/me/certifications", response_model=list[CertificationOut])
async def list_certs(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [CertificationOut.model_validate(c) for c in profile.certifications]


@router.post("/me/certifications", response_model=CertificationOut)
async def add_cert(body: CertificationIn, user: CandidateUser, db: DbSession):
    row = Certification(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return CertificationOut.model_validate(row)


@router.put("/me/certifications/{item_id}", response_model=CertificationOut)
async def update_cert(item_id: UUID, body: CertificationIn, user: CandidateUser, db: DbSession):
    row = await db.get(Certification, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return CertificationOut.model_validate(row)


@router.delete("/me/certifications/{item_id}")
async def delete_cert(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Certification, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Experience
@router.get("/me/experience", response_model=list[ExperienceOut])
async def list_exp(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [ExperienceOut.model_validate(e) for e in profile.experience]


@router.post("/me/experience", response_model=ExperienceOut)
async def add_exp(body: ExperienceIn, user: CandidateUser, db: DbSession):
    row = Experience(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return ExperienceOut.model_validate(row)


@router.put("/me/experience/{item_id}", response_model=ExperienceOut)
async def update_exp(item_id: UUID, body: ExperienceIn, user: CandidateUser, db: DbSession):
    row = await db.get(Experience, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return ExperienceOut.model_validate(row)


@router.delete("/me/experience/{item_id}")
async def delete_exp(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Experience, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Projects
@router.get("/me/projects", response_model=list[ProjectOut])
async def list_projects(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [ProjectOut.model_validate(p) for p in profile.projects]


@router.post("/me/projects", response_model=ProjectOut)
async def add_project(body: ProjectIn, user: CandidateUser, db: DbSession):
    row = Project(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return ProjectOut.model_validate(row)


@router.put("/me/projects/{item_id}", response_model=ProjectOut)
async def update_project(item_id: UUID, body: ProjectIn, user: CandidateUser, db: DbSession):
    row = await db.get(Project, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return ProjectOut.model_validate(row)


@router.delete("/me/projects/{item_id}")
async def delete_project(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Project, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Skills
@router.get("/me/skills")
async def get_skills(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return {"skills": [cs.skill.name for cs in profile.skills if cs.skill]}


@router.put("/me/skills")
async def put_skills(body: SkillsUpdate, user: CandidateUser, db: DbSession):
    await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == user.id))
    for name in body.skills:
        skill = await db.scalar(select(Skill).where(Skill.name == name))
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
            await db.flush()
        db.add(CandidateSkill(candidate_id=user.id, skill_id=skill.id))
    await db.flush()
    return {"skills": body.skills}


@router.get("/{candidate_id}", response_model=CandidateProfileOut)
async def get_candidate_public(candidate_id: UUID, user: CurrentUser, db: DbSession):
    return _to_out(await _load_profile(db, candidate_id))
