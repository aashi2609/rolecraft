"""ATS (Applicant Tracking System) resume scorer powered by Groq."""

from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from core.config import get_settings
from services.ai_client import AIServiceError, generate_content
from services.vertical_prompts import get_vertical_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ATSIssue:
    category: str
    description: str
    severity: str  # "high" | "medium" | "low"
    fix_suggestion: str


@dataclass
class ATSResult:
    overall_score: int
    breakdown: dict[str, int]
    issues: list[ATSIssue] = field(default_factory=list)
    passed: bool = False


_SCORER_SYSTEM = """\
You are an expert ATS (Applicant Tracking System) analyser. Your job is to score
a resume against industry standards for a specific job vertical.

Evaluate the resume on these 5 dimensions (each scored 0-100):
1. **keyword_match** — Does the resume contain keywords relevant to the target vertical?
2. **formatting** — Is the structure clean, parseable, and well-organised?
3. **experience_relevance** — How relevant is the candidate's experience to the target role?
4. **skills_alignment** — Do the listed skills match what employers in this vertical seek?
5. **quantification** — Are achievements backed by numbers, metrics, and measurable outcomes?

The overall_score is the weighted average:
  keyword_match × 0.25 + formatting × 0.15 + experience_relevance × 0.25
  + skills_alignment × 0.20 + quantification × 0.15

For any dimension scoring below 70, provide an issue with a concrete fix suggestion.

Return ONLY valid JSON matching this schema:
{
  "overall_score": <int 0-100>,
  "breakdown": {
    "keyword_match": <int>,
    "formatting": <int>,
    "experience_relevance": <int>,
    "skills_alignment": <int>,
    "quantification": <int>
  },
  "issues": [
    {
      "category": "<dimension name>",
      "description": "<what is wrong>",
      "severity": "high" | "medium" | "low",
      "fix_suggestion": "<specific actionable fix>"
    }
  ]
}
"""


def _fallback_score(vertical: str, skills: list[str]) -> ATSResult:
    """Deterministic fallback score when Groq is unavailable."""
    seed = int(
        hashlib.md5(f"{vertical}:{','.join(skills)}".encode()).hexdigest()[:8], 16
    )
    rng = random.Random(seed)
    base = 78 + rng.randint(0, 18) + min(6, len(skills))
    overall = min(98, base)
    return ATSResult(
        overall_score=overall,
        breakdown={
            "keyword_match": min(100, overall + rng.randint(-5, 5)),
            "formatting": min(100, overall + rng.randint(0, 8)),
            "experience_relevance": min(100, overall + rng.randint(-8, 5)),
            "skills_alignment": min(100, overall + rng.randint(-3, 7)),
            "quantification": min(100, overall + rng.randint(-10, 3)),
        },
        issues=[],
        passed=overall >= 80,
    )


async def score_resume(
    resume_content: dict[str, Any],
    target_vertical: str,
    job_description: Optional[str] = None,
) -> ATSResult:
    """Score a structured resume against ATS criteria for the target vertical.

    Falls back to a deterministic hash-based score when the Groq API key
    is empty or the call fails.
    """
    skills = resume_content.get("skills", {})
    if isinstance(skills, dict):
        all_skills = skills.get("technical", []) + skills.get("soft", [])
    elif isinstance(skills, list):
        all_skills = skills
    else:
        all_skills = []

    # Try AI scoring
    try:
        vp = get_vertical_prompt(target_vertical)

        prompt_parts = [
            f"## Target Vertical: {target_vertical}",
            f"## ATS Keywords to check for: {', '.join(vp.ats_keywords)}",
            "",
            "## Resume Content (JSON):",
            str(resume_content),
        ]
        if job_description:
            prompt_parts.insert(2, f"## Job Description:\n{job_description[:2000]}")

        prompt = "\n".join(prompt_parts)

        data = await generate_content(
            prompt,
            system_instruction=_SCORER_SYSTEM,
            model=settings.groq_ats_model,
            temperature=0.3,
            max_output_tokens=2048,
        )

        # Parse the response
        overall = int(data.get("overall_score", 75))
        breakdown_raw = data.get("breakdown", {})
        breakdown = {
            "keyword_match": int(breakdown_raw.get("keyword_match", 70)),
            "formatting": int(breakdown_raw.get("formatting", 80)),
            "experience_relevance": int(breakdown_raw.get("experience_relevance", 70)),
            "skills_alignment": int(breakdown_raw.get("skills_alignment", 70)),
            "quantification": int(breakdown_raw.get("quantification", 65)),
        }
        issues = []
        for issue_data in data.get("issues", []):
            issues.append(
                ATSIssue(
                    category=issue_data.get("category", "general"),
                    description=issue_data.get("description", ""),
                    severity=issue_data.get("severity", "medium"),
                    fix_suggestion=issue_data.get("fix_suggestion", ""),
                )
            )

        return ATSResult(
            overall_score=overall,
            breakdown=breakdown,
            issues=issues,
            passed=overall >= 80,
        )

    except (AIServiceError, Exception) as exc:
        logger.warning("ATS scoring fell back to deterministic: %s", exc)
        return _fallback_score(target_vertical, all_skills)
