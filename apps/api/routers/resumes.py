from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, DbSession, check_plan_limit
from models import CandidateProfile, CandidateSkill, Resume
from schemas import ResumeGenerateRequest, ResumeOut
from services.resume_service import generate_resume_for_vertical

router = APIRouter(prefix="/resumes", tags=["resumes"])


async def _profile_with_skills(db, user_id: UUID) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
        )
        .where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")
    return profile


@router.post("/generate", response_model=list[ResumeOut])
async def generate(body: ResumeGenerateRequest, user: CandidateUser, db: DbSession):
    if not body.target_verticals:
        raise HTTPException(status_code=400, detail="Select at least one target vertical")

    await check_plan_limit(user, db, "resume_verticals", extra=len(body.target_verticals))

    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    created: list[Resume] = []

    for i, vertical in enumerate(body.target_verticals):
        payload = await generate_resume_for_vertical(profile, vertical, skill_names)
        resume = Resume(
            candidate_id=user.id,
            target_vertical=vertical,
            content=payload["content"],
            ats_score=payload["ats_score"],
            embedding=payload["embedding"],
            is_default=i == 0,
        )
        db.add(resume)
        created.append(resume)

    await db.flush()
    for r in created:
        await db.refresh(r)
    return [ResumeOut.model_validate(r) for r in created]


@router.get("", response_model=list[ResumeOut])
async def list_resumes(user: CandidateUser, db: DbSession):
    rows = (
        await db.execute(
            select(Resume).where(Resume.candidate_id == user.id).order_by(Resume.created_at.desc())
        )
    ).scalars().all()
    return [ResumeOut.model_validate(r) for r in rows]


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    return ResumeOut.model_validate(row)


@router.post("/{resume_id}/regenerate", response_model=ResumeOut)
async def regenerate(resume_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    payload = await generate_resume_for_vertical(profile, row.target_vertical, skill_names)
    row.content = payload["content"]
    row.ats_score = payload["ats_score"]
    row.embedding = payload["embedding"]
    await db.flush()
    await db.refresh(row)
    return ResumeOut.model_validate(row)
