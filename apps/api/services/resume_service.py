"""Stage-2 resume generation — Groq-powered AI with auto-fix loop.

Falls back to the deterministic Stage-1 logic when GROQ_API_KEY is empty.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from core.config import get_settings
from models import CandidateProfile, CandidateSkill, Resume
from services.ai_client import AIServiceError, generate_content
from services.ats_scorer import ATSResult, score_resume
from services.data_cleaner import CleanedProfile, clean_profile
from services.embedding_service import embed_text
from services.vertical_prompts import classify_vertical, get_vertical_prompt

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Stage-1 deterministic fallback ────────────────────────────────────────────

VERTICAL_EMPHASIS = {
    "electronics": [
        "circuit design",
        "embedded systems",
        "lab work",
        "hardware projects",
    ],
    "software": ["programming projects", "software skills", "APIs", "version control"],
    "marketing": ["communication", "campaigns", "analytics", "client-facing work"],
    "design": ["UI/UX craft", "prototyping", "user research", "visual systems"],
    "sales": ["pipeline", "client relations", "negotiation", "CRM"],
    "data": ["SQL", "analytics", "insight generation", "quantitative coursework"],
    "general": ["transferable strengths", "problem solving", "collaboration"],
}


def _score_for(vertical: str, skills: list[str]) -> int:
    seed = int(
        hashlib.md5(f"{vertical}:{','.join(skills)}".encode()).hexdigest()[:8], 16
    )
    rng = random.Random(seed)
    return min(98, 78 + rng.randint(0, 18) + min(6, len(skills)))


async def _generate_deterministic(
    profile: CandidateProfile,
    vertical: str,
    skill_names: list[str],
) -> dict[str, Any]:
    """Original Stage-1 stub — kept as fallback."""
    bucket = classify_vertical(vertical)
    emphasis = VERTICAL_EMPHASIS.get(bucket, VERTICAL_EMPHASIS["general"])
    mapping_notes = {
        "electronics": "Emphasized core coursework, circuit/hardware projects, and lab experience.",
        "software": "Surfaced programming projects and coding-adjacent coursework from the profile.",
        "marketing": "Foregrounded communication/campaign signals; de-emphasized deep programming detail.",
        "design": "Centered UX/UI craft and product sense from available history.",
        "sales": "Highlighted client-facing and pipeline-oriented experience.",
        "data": "Centered analytical tools and quantitative signals.",
    }.get(bucket, f"Mapped strongest transferable signals to {vertical}.")

    highlighted = skill_names[:8] or emphasis[:4]
    content = {
        "vertical": vertical,
        "professional_summary": f"Profile tailored for {vertical}, emphasizing {', '.join(emphasis[:2])}.",
        "summary": f"Profile tailored for {vertical}, emphasizing {', '.join(emphasis[:2])}.",
        "emphasis": emphasis,
        "highlightedSkills": highlighted,
        "skills": {"technical": highlighted[:5], "soft": ["Communication", "Teamwork"]},
        "mappingNotes": mapping_notes,
        "experience": [
            {
                "title": e.role or e.designation or "Role",
                "company": e.company_name or "Company",
                "dates": f"{e.from_date or ''} – {e.to_date or 'Present'}",
                "bullets": [e.responsibilities or "Contributed to team objectives."],
            }
            for e in (profile.experience or [])[:3]
        ],
        "education": [
            {
                "degree": f"{ed.degree or ''}{(' in ' + ed.field_of_study) if ed.field_of_study else ''}".strip()
                or "Degree",
                "institution": ed.institute or "Institution",
                "year": str(ed.passing_year or ""),
                "gpa": ed.cgpa or "",
                "highlights": [],
            }
            for ed in (profile.education or [])[:2]
        ],
        "projects": [
            {
                "name": p.project_name or "Project",
                "description": p.responsibilities or "",
                "bullets": [
                    b.strip() for b in (p.achievements or "").split("\n") if b.strip()
                ]
                or ([p.responsibilities] if p.responsibilities else []),
                "technologies": [
                    t.strip() for t in (p.tools_used or "").split(",") if t.strip()
                ],
                "url": (
                    p.org
                    if p.org and ("http" in p.org or p.org.startswith("www."))
                    else ""
                ),
            }
            for p in (profile.projects or [])[:3]
        ],
        "certifications": [
            {"name": c.name, "issuer": c.issuing_org or ""}
            for c in (profile.certifications or [])[:5]
        ],
    }
    score = _score_for(vertical, skill_names)
    embedding_text = (
        f"{vertical} {' '.join(highlighted)} {content['summary']} {mapping_notes}"
    )
    embedding = await embed_text(embedding_text)
    return {
        "content": content,
        "ats_score": score,
        "ats_breakdown": None,
        "embedding": embedding,
        "generation_metadata": {"method": "deterministic", "model": None},
    }


# ── AI-powered generation ────────────────────────────────────────────────────

_WRITER_SYSTEM = """\
You are an expert resume writer who specialises in crafting ATS-optimised resumes.
Your resumes consistently score 85+ on ATS systems because you:

1. Use strong action verbs to start every bullet point
2. Quantify achievements with numbers, percentages, and metrics wherever possible
3. Include relevant industry keywords naturally throughout
4. Structure content for both human readers and automated parsers
5. Tailor emphasis based on the target vertical — highlighting transferable skills
   from unrelated experience when the candidate is switching domains

CRITICAL RULES:
- NEVER fabricate experience, skills, or achievements that are not in the profile
- DO reframe and emphasise existing experience for the target vertical
- DO identify transferable skills from seemingly unrelated backgrounds
- If the profile is sparse, work with what is available — do NOT invent data
- Write professional, concise bullet points (1-2 lines each)
- Use present tense for current roles, past tense for previous ones

Return ONLY valid JSON matching this exact schema:
{
  "professional_summary": "<2-3 sentence professional summary tailored for the vertical>",
  "experience": [
    {
      "title": "<job title>",
      "company": "<company name>",
      "dates": "<start – end>",
      "bullets": ["<achievement/responsibility>", ...]
    }
  ],
  "education": [
    {
      "degree": "<degree name>",
      "institution": "<school/university>",
      "year": "<graduation year or expected>",
      "highlights": ["<relevant coursework or honour>", ...]
    }
  ],
  "skills": {
    "technical": ["<skill>", ...],
    "soft": ["<skill>", ...]
  },
  "projects": [
    {
      "name": "<project name>",
      "description": "<1-2 sentence description emphasising impact>",
      "technologies": ["<tech>", ...]
    }
  ],
  "certifications": [
    {
      "name": "<certification name>",
      "issuer": "<issuing organisation>"
    }
  ],
  "emphasis": ["<area emphasised>", ...],
  "de_emphasized": ["<area de-emphasised>", ...],
  "mapping_notes": "<1-2 sentences explaining the cross-domain mapping strategy>"
}
"""

_FIX_SYSTEM = """\
You are an ATS resume optimisation expert. You will receive a resume that scored
below the passing threshold, along with specific issues identified by an ATS analyser.

Fix ONLY the identified issues. Do NOT rewrite the entire resume. Preserve the
overall structure and factual content.

For each issue:
- Apply the suggested fix
- Ensure the change improves the specific dimension that was flagged
- Keep all existing truthful content intact

Return the COMPLETE updated resume as valid JSON with the same schema as the input.
"""


def _build_profile_prompt(cleaned: CleanedProfile, vertical: str) -> str:
    """Assemble the user prompt from cleaned profile data."""
    vp = get_vertical_prompt(vertical)

    sections = [
        f"## Target Vertical: {vertical}",
        "",
        f"## Vertical-Specific Guidance:",
        f"- Tone: {vp.resume_tone}",
        f"- Emphasis: {vp.emphasis_rules}",
        f"- De-emphasis: {vp.de_emphasis_rules}",
        f"- Key skills for this vertical: {', '.join(vp.key_skills[:10])}",
        "",
        "## Candidate Profile:",
    ]
    if cleaned.name:
        sections.append(f"- Name: {cleaned.name}")
    if cleaned.email:
        sections.append(f"- Email: {cleaned.email}")
    sections.append(f"- Career Level: {cleaned.career_level}")

    if cleaned.skills:
        sections.append(f"- Skills: {', '.join(cleaned.skills)}")

    if cleaned.strengths:
        sections.append(f"- Strengths: {', '.join(cleaned.strengths)}")

    if cleaned.education:
        sections.append("\n### Education:")
        for edu in cleaned.education:
            parts = []
            if edu.get("degree"):
                parts.append(edu["degree"])
            if edu.get("field_of_study"):
                parts.append(f"in {edu['field_of_study']}")
            if edu.get("institution"):
                parts.append(f"at {edu['institution']}")
            if edu.get("year"):
                parts.append(f"({edu['year']})")
            if edu.get("cgpa"):
                parts.append(f"CGPA: {edu['cgpa']}")
            sections.append(f"  - {' '.join(parts)}")

    if cleaned.experience:
        sections.append("\n### Experience:")
        for exp in cleaned.experience:
            line = f"  - {exp.get('title', 'Role')}"
            if exp.get("company"):
                line += f" at {exp['company']}"
            if exp.get("from_date"):
                line += f" ({exp['from_date']} – {exp.get('to_date', 'Present')})"
            sections.append(line)
            if exp.get("responsibilities"):
                sections.append(
                    f"    Responsibilities: {exp['responsibilities'][:500]}"
                )

    if cleaned.projects:
        sections.append("\n### Projects:")
        for proj in cleaned.projects:
            line = f"  - {proj.get('name', 'Project')}"
            if proj.get("organization"):
                line += f" ({proj['organization']})"
            sections.append(line)
            if proj.get("description"):
                sections.append(f"    {proj['description'][:300]}")
            if proj.get("technologies"):
                sections.append(f"    Tools: {proj['technologies']}")

    if cleaned.certifications:
        sections.append("\n### Certifications:")
        for cert in cleaned.certifications:
            line = f"  - {cert['name']}"
            if cert.get("issuer"):
                line += f" ({cert['issuer']})"
            sections.append(line)

    sections.append(
        "\n\nGenerate a tailored, ATS-optimised resume for the target vertical. "
        "Reframe the candidate's background to maximise relevance."
    )

    return "\n".join(sections)


async def _generate_ai(
    cleaned: CleanedProfile,
    vertical: str,
) -> dict[str, Any]:
    """Generate resume content via Gemini AI."""
    prompt = _build_profile_prompt(cleaned, vertical)

    data = await generate_content(
        prompt,
        system_instruction=_WRITER_SYSTEM,
        model=settings.groq_model,
        temperature=0.7,
        max_output_tokens=4096,
    )

    # Ensure backward-compatible fields
    content = dict(data)
    content.setdefault("vertical", vertical)
    content.setdefault("summary", content.get("professional_summary", ""))
    content.setdefault("mappingNotes", content.get("mapping_notes", ""))

    # Flatten highlightedSkills for backward compat
    skills = content.get("skills", {})
    if isinstance(skills, dict):
        highlighted = skills.get("technical", []) + skills.get("soft", [])
    elif isinstance(skills, list):
        highlighted = skills
    else:
        highlighted = []
    content["highlightedSkills"] = highlighted[:10]

    # highlightedExperience for backward compat
    content["highlightedExperience"] = [
        f"{exp.get('title', 'Role')} @ {exp.get('company', 'Company')}"
        for exp in content.get("experience", [])[:3]
    ]
    content["highlightedEducation"] = [
        f"{edu.get('degree', '')} at {edu.get('institution', '')}".strip()
        for edu in content.get("education", [])[:2]
    ]

    return content


async def _fix_with_ai(
    resume_content: dict[str, Any],
    ats_result: ATSResult,
    vertical: str,
) -> dict[str, Any]:
    """Send the resume + ATS issues back to Gemini for targeted fixes."""
    issues_text = "\n".join(
        f"- [{issue.severity.upper()}] {issue.category}: {issue.description}\n"
        f"  Suggestion: {issue.fix_suggestion}"
        for issue in ats_result.issues
    )

    prompt = (
        f"## Current Resume (JSON):\n{json.dumps(resume_content, indent=2)}\n\n"
        f"## ATS Score: {ats_result.overall_score}/100\n\n"
        f"## Issues to Fix:\n{issues_text}\n\n"
        f"## Target Vertical: {vertical}\n\n"
        "Fix the issues above and return the complete updated resume JSON."
    )

    data = await generate_content(
        prompt,
        system_instruction=_FIX_SYSTEM,
        model=settings.groq_model,
        temperature=0.5,
        max_output_tokens=4096,
    )

    # Preserve backward-compat fields
    content = dict(data)
    content.setdefault("vertical", vertical)
    content.setdefault("summary", content.get("professional_summary", ""))
    content.setdefault("mappingNotes", content.get("mapping_notes", ""))

    skills = content.get("skills", {})
    if isinstance(skills, dict):
        highlighted = skills.get("technical", []) + skills.get("soft", [])
    elif isinstance(skills, list):
        highlighted = skills
    else:
        highlighted = []
    content["highlightedSkills"] = highlighted[:10]
    content["highlightedExperience"] = [
        f"{exp.get('title', 'Role')} @ {exp.get('company', 'Company')}"
        for exp in content.get("experience", [])[:3]
    ]
    content["highlightedEducation"] = [
        f"{edu.get('degree', '')} at {edu.get('institution', '')}".strip()
        for edu in content.get("education", [])[:2]
    ]

    return content


# ── Public API ────────────────────────────────────────────────────────────────


async def generate_resume_for_vertical(
    profile: CandidateProfile,
    vertical: str,
    skill_names: list[str],
    *,
    user_email: str = "",
) -> dict[str, Any]:
    """Generate a single vertical resume — AI with auto-fix, or deterministic fallback."""
    # Try AI path
    if settings.groq_api_key:
        try:
            logger.info(
                "Attempting AI-powered resume generation for vertical: %s", vertical
            )
            return await generate_with_autofix(
                profile, vertical, skill_names, user_email=user_email
            )
        except AIServiceError as exc:
            logger.warning("AI service error, falling back to deterministic: %s", exc)
        except Exception as exc:
            logger.error(
                "Unexpected error during AI generation, falling back to deterministic: %s",
                exc,
                exc_info=True,
            )

    # Deterministic fallback
    logger.info("Using deterministic resume generation for vertical: %s", vertical)
    return await _generate_deterministic(profile, vertical, skill_names)


async def generate_with_autofix(
    profile: CandidateProfile,
    vertical: str,
    skill_names: list[str],
    *,
    user_email: str = "",
) -> dict[str, Any]:
    """Full AI pipeline: clean → generate → score → fix loop → embed."""
    max_iterations = settings.resume_max_fix_iterations
    started_at = datetime.now(timezone.utc).isoformat()

    # Step 1: Clean profile data
    cleaned = clean_profile(profile, user_email=user_email)

    # Step 2: Generate initial resume
    content = await _generate_ai(cleaned, vertical)

    # Step 3: Score it
    ats_result = await score_resume(content, vertical)
    best_content = content
    best_score = ats_result.overall_score
    best_breakdown = ats_result.breakdown

    iterations = [
        {
            "iteration": 1,
            "score": ats_result.overall_score,
            "passed": ats_result.passed,
            "issues_count": len(ats_result.issues),
        }
    ]

    # Step 4: Auto-fix loop
    current_content = content
    current_ats = ats_result

    for i in range(2, max_iterations + 1):
        if current_ats.passed or not current_ats.issues:
            break

        try:
            fixed_content = await _fix_with_ai(current_content, current_ats, vertical)
            fixed_ats = await score_resume(fixed_content, vertical)

            iterations.append(
                {
                    "iteration": i,
                    "score": fixed_ats.overall_score,
                    "passed": fixed_ats.passed,
                    "issues_count": len(fixed_ats.issues),
                }
            )

            if fixed_ats.overall_score > best_score:
                best_content = fixed_content
                best_score = fixed_ats.overall_score
                best_breakdown = fixed_ats.breakdown

            current_content = fixed_content
            current_ats = fixed_ats

        except Exception as exc:
            logger.warning("Auto-fix iteration %d failed: %s", i, exc)
            iterations.append(
                {
                    "iteration": i,
                    "score": None,
                    "error": str(exc),
                }
            )
            break

    # Step 5: Generate embedding
    highlighted = best_content.get("highlightedSkills", skill_names[:8])
    summary = best_content.get("summary", best_content.get("professional_summary", ""))
    mapping_notes = best_content.get(
        "mappingNotes", best_content.get("mapping_notes", "")
    )
    embedding_text = f"{vertical} {' '.join(highlighted)} {summary} {mapping_notes}"
    embedding = await embed_text(embedding_text)

    return {
        "content": best_content,
        "ats_score": best_score,
        "ats_breakdown": best_breakdown,
        "embedding": embedding,
        "generation_metadata": {
            "method": "ai",
            "model": settings.groq_model,
            "iterations": iterations,
            "final_score": best_score,
            "cleaning_warnings": cleaned.warnings,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def get_or_generate_resume(
    db,
    candidate_id: UUID,
    target_vertical: str,
    user_email: str,
) -> UUID | None:
    """Get an existing resume for the vertical, or generate a new one.

    Returns the resume_id, or None if generation fails and no fallback exists.
    Caller must enforce plan limits before invoking this when generating.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    existing = await db.scalar(
        select(Resume).where(
            Resume.candidate_id == candidate_id,
            Resume.target_vertical == target_vertical,
        )
    )
    if existing:
        return existing.id

    profile = await db.scalar(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.certifications),
            selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
        )
        .where(CandidateProfile.user_id == candidate_id)
    )
    if not profile:
        raise ValueError("Complete your profile first to generate a resume")

    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]

    try:
        payload = await generate_resume_for_vertical(
            profile, target_vertical, skill_names, user_email=user_email
        )
        resume = Resume(
            candidate_id=candidate_id,
            target_vertical=target_vertical,
            content=payload["content"],
            ats_score=payload["ats_score"],
            ats_breakdown=payload.get("ats_breakdown"),
            generation_metadata=payload.get("generation_metadata"),
            embedding=payload["embedding"],
            is_default=False,
        )
        db.add(resume)
        await db.flush()
        return resume.id
    except Exception as exc:
        logger.error("Failed to dynamically generate resume: %s", exc)
        resume = await db.scalar(
            select(Resume)
            .where(Resume.candidate_id == candidate_id)
            .order_by(Resume.is_default.desc(), Resume.created_at.desc())
        )
        return resume.id if resume else None


_PARSE_SYSTEM = "You are a strict JSON returning AI. You must return only the JSON."

_PARSE_PROMPT = """\
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
{text}
"""


async def parse_resume_pdf(
    db,
    candidate_id: UUID,
    file_data: bytes,
) -> dict[str, Any]:
    """Parse already-validated PDF bytes and extract structured data via Groq.

    Caller must validate upload type/size before passing ``file_data``.
    """
    import io

    import pypdf
    from fastapi import HTTPException

    from core.config import get_settings

    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="Resume parsing requires GROQ_API_KEY. Add it to apps/api/.env and restart the API.",
        )

    if not file_data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to read PDF: {exc}"
        ) from exc

    prompt = _PARSE_PROMPT.format(text=text[:15000])

    try:
        return await generate_content(
            prompt=prompt,
            system_instruction=_PARSE_SYSTEM,
            response_mime_type="application/json",
        )
    except AIServiceError as exc:
        from fastapi import HTTPException as HTTPExc

        raise HTTPExc(status_code=502, detail=f"Groq AI unavailable: {exc}") from exc
    except Exception as exc:
        from fastapi import HTTPException as HTTPExc

        raise HTTPExc(
            status_code=500, detail=f"Failed to parse resume with AI: {exc}"
        ) from exc
