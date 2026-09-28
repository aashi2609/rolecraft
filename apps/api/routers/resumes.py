from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, DbSession, check_plan_limit
from models import CandidateProfile, CandidateSkill, PlanTier, Resume, Subscription
from schemas import ResumeGenerateRequest, ResumeOut
from services.pdf_service import build_resume_pdf_response, resolve_candidate_name
from services.resume_service import generate_resume_for_vertical, parse_resume_pdf

router = APIRouter(prefix="/resumes", tags=["resumes"])

# Plan tiers that include resume generation (not Job Search)
_GENERATION_TIERS = {
    PlanTier.resume_builder,
    PlanTier.complete,
    # Legacy tiers that also had resume generation
    PlanTier.premium,
    PlanTier.elite,
}


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


def _resume_to_out(resume: Resume, profile_updated_at=None) -> ResumeOut:
    """Convert a Resume ORM object to ResumeOut with computed is_stale."""
    is_stale = False
    if profile_updated_at and resume.generated_from_profile_at:
        is_stale = profile_updated_at > resume.generated_from_profile_at
    elif profile_updated_at and not resume.generated_from_profile_at:
        # Resume was created before stale tracking existed
        is_stale = False
    out = ResumeOut.model_validate(resume)
    out.is_stale = is_stale
    return out


async def _get_profile_updated_at(db, user_id: UUID):
    """Get the profile_updated_at timestamp for stale computation."""
    result = await db.execute(
        select(CandidateProfile.profile_updated_at).where(
            CandidateProfile.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _can_generate(db, user_id: UUID) -> tuple[bool, str | None]:
    """Check if the user's plan includes resume generation."""
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
    ).scalar_one_or_none()
    if not sub:
        return True, None  # No subscription = free tier, let check_plan_limit handle caps
    if sub.plan_tier in _GENERATION_TIERS:
        return True, None
    return False, "Your current plan doesn't include resume generation. Upgrade to Resume Builder or Complete."


@router.post("/generate", response_model=list[ResumeOut])
async def generate(body: ResumeGenerateRequest, user: CandidateUser, db: DbSession):
    if not body.target_verticals:
        raise HTTPException(
            status_code=400, detail="Select at least one target vertical"
        )

    await check_plan_limit(
        user, db, "resume_verticals", extra=len(body.target_verticals)
    )

    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    created: list[Resume] = []

    for i, vertical in enumerate(body.target_verticals):
        payload = await generate_resume_for_vertical(
            profile, vertical, skill_names, user_email=user.email
        )
        resume = Resume(
            candidate_id=user.id,
            target_vertical=vertical,
            content=payload["content"],
            ats_score=payload["ats_score"],
            ats_breakdown=payload.get("ats_breakdown"),
            generation_metadata=payload.get("generation_metadata"),
            embedding=payload["embedding"],
            is_default=i == 0,
            generated_from_profile_at=profile.profile_updated_at,
        )
        db.add(resume)
        created.append(resume)

    await db.flush()
    for r in created:
        await db.refresh(r)
    return [_resume_to_out(r, profile.profile_updated_at) for r in created]


@router.get("", response_model=list[ResumeOut])
async def list_resumes(user: CandidateUser, db: DbSession):
    profile_updated_at = await _get_profile_updated_at(db, user.id)
    rows = (
        (
            await db.execute(
                select(Resume)
                .where(Resume.candidate_id == user.id)
                .order_by(Resume.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_resume_to_out(r, profile_updated_at) for r in rows]


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    profile_updated_at = await _get_profile_updated_at(db, user.id)
    return _resume_to_out(row, profile_updated_at)


@router.post("/{resume_id}/regenerate", response_model=ResumeOut)
async def regenerate(resume_id: UUID, user: CandidateUser, db: DbSession):
    old = await db.get(Resume, resume_id)
    if not old or old.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    # Check plan allows generation
    can_gen, err_msg = await _can_generate(db, user.id)
    if not can_gen:
        raise HTTPException(status_code=403, detail=err_msg)

    # Regenerating an existing vertical does not consume a free-plan slot.
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    payload = await generate_resume_for_vertical(
        profile, old.target_vertical, skill_names, user_email=user.email
    )

    # Archive the old resume: unset default, keep it for existing applications
    was_default = old.is_default
    old.is_default = False

    # Create NEW version
    new_resume = Resume(
        candidate_id=user.id,
        target_vertical=old.target_vertical,
        content=payload["content"],
        ats_score=payload["ats_score"],
        ats_breakdown=payload.get("ats_breakdown"),
        generation_metadata=payload.get("generation_metadata"),
        embedding=payload["embedding"],
        version=(old.version or 1) + 1,
        is_default=was_default,
        generated_from_profile_at=profile.profile_updated_at,
    )
    db.add(new_resume)
    await db.flush()
    await db.refresh(new_resume)
    return _resume_to_out(new_resume, profile.profile_updated_at)


@router.post("/{resume_id}/mark-current", response_model=ResumeOut)
async def mark_current(resume_id: UUID, user: CandidateUser, db: DbSession):
    """Clear stale flag without regenerating content (API-key / demo backup)."""
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    profile_updated_at = await _get_profile_updated_at(db, user.id)
    if not profile_updated_at:
        raise HTTPException(status_code=404, detail="Complete your profile first")

    row.generated_from_profile_at = profile_updated_at
    await db.flush()
    await db.refresh(row)
    return _resume_to_out(row, profile_updated_at)


@router.post("/{resume_id}/improve", response_model=ResumeOut)
async def improve(resume_id: UUID, user: CandidateUser, db: DbSession):
    """Trigger another auto-fix iteration on an existing resume."""
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    # Improve updates the same resume — no extra plan slot.
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
    row.generated_from_profile_at = profile.profile_updated_at
    await db.flush()
    await db.refresh(row)
    return _resume_to_out(row, profile.profile_updated_at)


@router.get("/{resume_id}/download")
@router.get("/{resume_id}/pdf")
async def download_pdf(resume_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    profile = (
        await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
    ).scalar_one_or_none()
    weblinks = (profile.weblinks or {}) if profile else {}
    filename = f"resume_{row.target_vertical.replace(' ', '_').lower()}_v{row.version or 1}.pdf"
    return build_resume_pdf_response(
        resume_content=row.content or {},
        email=user.email,
        weblinks=weblinks,
        filename=filename,
        candidate_name=resolve_candidate_name(weblinks=weblinks, email=user.email),
        location=(profile.preferred_locations or [None])[0] if profile else "",
    )


class TailoredResumeRequest(BaseModel):
    target_role: str


@router.post("/download-tailored")
async def download_tailored_resume(
    body: TailoredResumeRequest, user: CandidateUser, db: DbSession
):
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
        candidate_name=resolve_candidate_name(
            weblinks=profile.weblinks or {}, email=user.email
        ),
        location=(profile.preferred_locations or [None])[0] or "",
    )


@router.post("/parse")
async def parse_resume(
    user: CandidateUser, db: DbSession, file: UploadFile = File(...)
):
    await check_plan_limit(user, db, "resume_verticals", extra=1)

    from core.upload_limits import validate_upload

    data, _, _ = await validate_upload(file, "document")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    return await parse_resume_pdf(db, user.id, data)
