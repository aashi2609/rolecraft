from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
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


@router.get("/{resume_id}/pdf")
async def download_pdf(resume_id: UUID, user: CandidateUser, db: DbSession):
    """Generate and return a PDF of the resume."""
    row = await db.get(Resume, resume_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    from services.pdf_service import generate_pdf

    # Get candidate name from profile
    profile = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    candidate = profile.scalar_one_or_none()
    candidate_name = "Candidate"
    weblinks = {}
    if candidate:
        # Try to build a name from the profile; fall back to email
        candidate_name = user.email.split("@")[0].replace(".", " ").title()
        weblinks = candidate.weblinks or {}

    content = row.content or {}
    try:
        pdf_bytes = generate_pdf(
            resume_content=content,
            candidate_name=candidate_name,
            email=user.email,
            weblinks=weblinks,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    # Determine content type
    is_pdf = pdf_bytes[:4] == b"%PDF"
    media_type = "application/pdf" if is_pdf else "text/html"
    ext = "pdf" if is_pdf else "html"
    filename = f"resume_{row.target_vertical.replace(' ', '_').lower()}_v{row.version or 1}.{ext}"

    return Response(
        content=pdf_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

from pydantic import BaseModel

class TailoredResumeRequest(BaseModel):
    target_role: str

@router.post("/download-tailored")
async def download_tailored_resume(body: TailoredResumeRequest, user: CandidateUser, db: DbSession):
    """Generate and return a PDF of a resume tailored to a specific role without saving it."""
    await check_plan_limit(user, db, "resume_verticals", extra=1)
    profile = await _profile_with_skills(db, user.id)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    
    # Generate content using AI
    payload = await generate_resume_for_vertical(
        profile, body.target_role, skill_names, user_email=user.email
    )
    content = payload["content"]

    from services.pdf_service import generate_pdf
    
    # Get candidate name from profile
    candidate_name = user.email.split("@")[0].replace(".", " ").title()
    weblinks = profile.weblinks or {}

    try:
        pdf_bytes = generate_pdf(
            resume_content=content,
            candidate_name=candidate_name,
            email=user.email,
            weblinks=weblinks,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    is_pdf = pdf_bytes[:4] == b"%PDF"
    media_type = "application/pdf" if is_pdf else "text/html"
    ext = "pdf" if is_pdf else "html"
    filename = f"resume_{body.target_role.replace(' ', '_').lower()}.{ext}"

    return Response(
        content=pdf_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/parse")
async def parse_resume(user: CandidateUser, db: DbSession, file: UploadFile = File(...)):
    await check_plan_limit(user, db, "resume_verticals", extra=1)

    import io

    import pypdf

    from core.config import get_settings
    from core.upload_limits import validate_upload
    from services.ai_client import AIServiceError, generate_content

    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="Resume parsing requires GROQ_API_KEY. Add it to apps/api/.env and restart the API.",
        )

    data, _, _ = await validate_upload(file, "document")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {exc}") from exc

    prompt = f"""
    You are an expert resume parser. Extract the following information from the provided resume text and return it as a structured JSON object.
    
    The JSON object MUST have this exact schema:
    {{
        "career_level": "Entry Level, Mid Level, or Senior Level",
        "gender": "Male, Female, or Other",
        "marital_status": "Single, Married, etc",
        "present_address": "Full address",
        "strengths": ["list", "of", "strengths"],
        "weblinks": {{"LinkedIn": "url", "GitHub": "url"}},
        "education": [
            {{
                "qualification_level": "Bachelor, Master, etc",
                "degree": "Degree name",
                "institute": "Institution name",
                "field_of_study": "Major",
                "passing_year": 2020,
                "cgpa": "Grade"
            }}
        ],
        "experience": [
            {{
                "company_name": "Company",
                "role": "Role name",
                "designation": "Designation",
                "from_date": "YYYY-MM-DD",
                "to_date": "YYYY-MM-DD",
                "is_current": true/false,
                "responsibilities": "Description of work"
            }}
        ],
        "projects": [
            {{
                "project_name": "Project name",
                "tools_used": "Tools used",
                "from_date": "YYYY-MM-DD",
                "to_date": "YYYY-MM-DD",
                "responsibilities": "What they did"
            }}
        ],
        "certifications": [
            {{
                "name": "Cert name",
                "issuing_org": "Org"
            }}
        ],
        "skills": ["Python", "React", "SQL"]
    }}

    If a field is not found in the resume, omit it or set it to null. Ensure dates are in YYYY-MM-DD format if possible, or null.
    
    RESUME TEXT:
    {text[:15000]}
    """
    
    try:
        parsed_data = await generate_content(
            prompt=prompt,
            system_instruction="You are a strict JSON returning AI. You must return only the JSON.",
            response_mime_type="application/json"
        )
        return parsed_data
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=f"Groq AI unavailable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume with AI: {exc}") from exc

