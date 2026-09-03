"""Unit tests for fitment rationale (template + LLM flag fallback)."""
from __future__ import annotations

import asyncio

from services.fitment_rationale_service import generate_fitment_rationale, template_rationale


def test_template_rationale_skill_overlap() -> None:
    text = template_rationale(
        job_skills=["React", "TypeScript", "Python"],
        candidate_skills=["react", "node"],
    )
    assert "React" in text or "react" in text.lower()
    assert "overlap" in text.lower()


def test_template_rationale_no_skills_fallback() -> None:
    text = template_rationale(job_skills=[], candidate_skills=[])
    assert "experience" in text.lower() or "alignment" in text.lower()


def test_generate_fitment_rationale_uses_template_without_groq(monkeypatch) -> None:
    import services.fitment_rationale_service as frs

    monkeypatch.setattr(frs.settings, "groq_api_key", None)
    monkeypatch.setattr(frs.settings, "fitment_llm_rationales", True)

    text, source = asyncio.run(
        generate_fitment_rationale(
            job_title="Backend Engineer",
            job_department="Engineering",
            job_skills=["Python", "FastAPI"],
            candidate_name="Alex",
            candidate_title="Software Engineer",
            candidate_skills=["Python"],
            score=82.5,
        )
    )
    assert source == "template"
    assert len(text) >= 10
