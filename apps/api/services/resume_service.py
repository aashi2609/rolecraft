"""Stage-1 resume generation — deterministic stub (full AI in Stage 2)."""

from __future__ import annotations

import hashlib
import random
from typing import Any

from models import CandidateProfile
from services.fitment_service import embed_text


VERTICAL_EMPHASIS = {
    "electronics": ["circuit design", "embedded systems", "lab work", "hardware projects"],
    "software": ["programming projects", "software skills", "APIs", "version control"],
    "marketing": ["communication", "campaigns", "analytics", "client-facing work"],
    "design": ["UI/UX craft", "prototyping", "user research", "visual systems"],
    "sales": ["pipeline", "client relations", "negotiation", "CRM"],
    "data": ["SQL", "analytics", "insight generation", "quantitative coursework"],
    "general": ["transferable strengths", "problem solving", "collaboration"],
}


def _classify(vertical: str) -> str:
    v = vertical.lower()
    if any(k in v for k in ("electron", "ece", "hardware", "embedded")):
        return "electronics"
    if any(k in v for k in ("market", "seo", "brand", "content")):
        return "marketing"
    if any(k in v for k in ("design", "ui", "ux", "figma")):
        return "design"
    if any(k in v for k in ("sales", "account")):
        return "sales"
    if any(k in v for k in ("data", "analyst", "ml")):
        return "data"
    if any(k in v for k in ("software", "it", "developer", "engineer", "frontend", "backend")):
        return "software"
    return "general"


def _score_for(vertical: str, skills: list[str]) -> int:
    seed = int(hashlib.md5(f"{vertical}:{','.join(skills)}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return min(98, 78 + rng.randint(0, 18) + min(6, len(skills)))


async def generate_resume_for_vertical(
    profile: CandidateProfile,
    vertical: str,
    skill_names: list[str],
) -> dict[str, Any]:
    bucket = _classify(vertical)
    emphasis = VERTICAL_EMPHASIS[bucket]
    mapping_notes = {
        "electronics": "Emphasized core coursework, circuit/hardware projects, and lab experience.",
        "software": "Surfaced programming projects and coding-adjacent coursework from the profile.",
        "marketing": "Foregrounded communication/campaign signals; de-emphasized deep programming detail.",
        "design": "Centered UX/UI craft and product sense from available history.",
        "sales": "Highlighted client-facing and pipeline-oriented experience.",
        "data": "Centered analytical tools and quantitative signals.",
        "general": f"Mapped strongest transferable signals to {vertical}.",
    }[bucket]

    highlighted = skill_names[:8] or emphasis[:4]
    content = {
        "vertical": vertical,
        "summary": f"Profile tailored for {vertical}, emphasizing {', '.join(emphasis[:2])}.",
        "emphasis": emphasis,
        "highlightedSkills": highlighted,
        "mappingNotes": mapping_notes,
        "highlightedExperience": [
            f"{e.role or e.designation or 'Role'} @ {e.company_name or 'Company'}"
            for e in (profile.experience or [])[:3]
        ],
        "highlightedEducation": [
            f"{ed.degree or ''} {ed.field_of_study or ''}".strip() or (ed.institute or "Education")
            for ed in (profile.education or [])[:2]
        ],
    }
    score = _score_for(vertical, skill_names)
    embedding_text = f"{vertical} {' '.join(highlighted)} {content['summary']} {mapping_notes}"
    embedding = await embed_text(embedding_text)
    return {"content": content, "ats_score": score, "embedding": embedding}
