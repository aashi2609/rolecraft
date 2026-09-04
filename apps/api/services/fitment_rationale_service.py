"""Fitment rationale — Groq when configured, template fallback otherwise."""

from __future__ import annotations

import logging
from typing import Literal

from core.config import get_settings
from services.ai_client import AIServiceError, generate_content

logger = logging.getLogger(__name__)
settings = get_settings()

RationaleSource = Literal["llm", "template"]


def template_rationale(
    job_skills: list[str],
    candidate_skills: list[str] | None = None,
) -> str:
    job_set = {s.lower() for s in job_skills if s}
    cand_set = {s.lower() for s in (candidate_skills or []) if s}
    overlap = sorted(job_set & cand_set)[:3] if job_set and cand_set else []
    if overlap:
        return f"Strong skills overlap in {', '.join(overlap)}."
    top = [s for s in (candidate_skills or job_skills)[:3] if s]
    if top:
        return f"Strong skills overlap in {', '.join(top)}."
    return "Profile match based on experience and vertical alignment."


async def generate_fitment_rationale(
    *,
    job_title: str,
    job_department: str | None = None,
    job_skills: list[str],
    candidate_name: str,
    candidate_title: str | None,
    candidate_skills: list[str],
    score: float,
) -> tuple[str, RationaleSource]:
    fallback = template_rationale(job_skills, candidate_skills)
    if not settings.groq_api_key or not settings.fitment_llm_rationales:
        return fallback, "template"

    prompt = (
        f"Job: {job_title} ({job_department or 'general'})\n"
        f"Required skills: {', '.join(job_skills[:8]) or 'not specified'}\n"
        f"Candidate: {candidate_name} — {candidate_title or 'professional'}\n"
        f"Candidate skills: {', '.join(candidate_skills[:8]) or 'not specified'}\n"
        f"Match score (0-100): {score:.0f}\n\n"
        'Respond with JSON only: {"rationale": "2-3 honest sentences, max 280 chars"}'
    )
    try:
        parsed = await generate_content(
            prompt,
            system_instruction=(
                "Explain job-candidate fit honestly. Mention skill overlap or gaps. "
                "No hype. JSON object with single key rationale."
            ),
            temperature=0.4,
            max_output_tokens=256,
        )
        text = (parsed.get("rationale") or "").strip()
        if len(text) >= 20:
            return text[:500], "llm"
    except AIServiceError as exc:
        logger.info("Fitment LLM rationale fallback: %s", exc)

    return fallback, "template"
