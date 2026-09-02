from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, DbSession, check_plan_limit
from models import CandidateProfile, CandidateSkill, Resume
from schemas import ResumeGenerateRequest, ResumeOut
from services.resume_service import generate_resume_for_vertical, parse_resume_pdf
from services.pdf_service import build_resume_pdf_response


router = APIRouter(prefix="/resumes", tags=["resumes"])


async def _profile_with_skills(db, user_id: UUID) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.certifications),
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
        payload = await generate_resume_for_vertical(profile, vertical, skill_names, user_email=user.email)
        resume = Resume(
            candidate_id=user.id,
            target_vertical=vertical,
            content=payload["content"],
            ats_score=payload["ats_score"],
            ats_breakdown=payload.get("ats_breakdown"),
            generation_metadata=payload.get("generation_metadata"),
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
    await check_plan_limit(user, db, "resume_verticals", extra=1)
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    payload = await generate_resume_for_vertical(
        profile, row.target_vertical, skill_names, user_email=user.email
    )
    row.content = payload["content"]
    row.ats_score = payload["ats_score"]
    row.ats_breakdown = payload.get("ats_breakdown")
    row.generation_metadata = payload.get("generation_metadata")
    row.embedding = payload["embedding"]
    row.version = (row.version or 1) + 1
    row.pdf_path = None  # invalidate cached PDF
    await db.flush()
    await db.refresh(row)
    return ResumeOut.model_validate(row)


@router.post("/{resume_id}/improve", response_model=ResumeOut)
async def improve(resume_id: UUID, user: CandidateUser, db: DbSession):
    """Trigger another auto-fix iteration on an existing resume."""
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await check_plan_limit(user, db, "resume_verticals", extra=1)
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    payload = await generate_resume_for_vertical(
        profile, row.target_vertical, skill_names, user_email=user.email
    )
    row.content = payload["content"]
    row.ats_score = payload["ats_score"]
    row.ats_breakdown = payload.get("ats_breakdown")
    row.generation_metadata = payload.get("generation_metadata")
    row.embedding = payload["embedding"]
    row.version = (row.version or 1) + 1
    row.pdf_path = None
    await db.flush()
    await db.refresh(row)
    return ResumeOut.model_validate(row)


@router.get("/{resume_id}/download")
@router.get("/{resume_id}/pdf")
async def download_pdf(resume_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    profile = (
        await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    ).scalar_one_or_none()
    weblinks = (profile.weblinks or {}) if profile else {}
    filename = f"resume_{row.target_vertical.replace(' ', '_').lower()}_v{row.version or 1}.pdf"
    return build_resume_pdf_response(
        resume_content=row.content or {},
        email=user.email,
        weblinks=weblinks,
        filename=filename,
    )


from pydantic import BaseModel


class TailoredResumeRequest(BaseModel):
    target_role: str


@router.post("/download-tailored")
async def download_tailored_resume(body: TailoredResumeRequest, user: CandidateUser, db: DbSession):
    """Generate and return a PDF tailored to a role without saving it."""
    await check_plan_limit(user, db, "resume_verticals", extra=1)
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    payload = await generate_resume_for_vertical(
        profile, body.target_role, skill_names, user_email=user.email
    )
    filename = f"resume_{body.target_role.replace(' ', '_').lower()}.pdf"
    return build_resume_pdf_response(
        resume_content=payload["content"],
        email=user.email,
        weblinks=profile.weblinks or {},
        filename=filename,
    )


@router.post("/parse")
async def parse_resume(user: CandidateUser, db: DbSession, file: UploadFile = File(...)):
    await check_plan_limit(user, db, "resume_verticals", extra=1)

    from core.upload_limits import validate_upload

    data, _, _ = await validate_upload(file, "document")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    return await parse_resume_pdf(db, user.id, data)

