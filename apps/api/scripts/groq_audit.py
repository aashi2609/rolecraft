"""Live Groq integration audit — run from apps/api with PYTHONPATH=."""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

from core.config import get_settings
from services.ai_client import AIServiceError, generate_content
from services.ats_scorer import score_resume
from services.data_cleaner import CleanedProfile
from services.resume_service import _generate_ai


async def list_groq_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return sorted(m["id"] for m in data.get("data", []))


async def test_missing_key() -> str:
    from services import ai_client

    original = ai_client.settings.groq_api_key
    ai_client.settings.groq_api_key = ""
    try:
        await generate_content("hi")
        return "FAIL: expected AIServiceError"
    except AIServiceError as exc:
        return f"OK: {exc}"
    finally:
        ai_client.settings.groq_api_key = original


async def main() -> None:
    s = get_settings()
    key = s.groq_api_key
    masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "(empty)"
    print("=== CONFIG ===")
    print(f"GROQ_API_KEY loaded: {bool(key)} ({masked})")
    print(f"groq_model: {s.groq_model}")
    print(f"groq_ats_model: {s.groq_ats_model}")
    print()

    if not key:
        print("Cannot run live tests — GROQ_API_KEY not set in .env")
        sys.exit(1)

    print("=== MODEL AVAILABILITY ===")
    try:
        models = await list_groq_models(key)
        for name in (s.groq_model, s.groq_ats_model):
            status = "AVAILABLE" if name in models else "NOT FOUND"
            print(f"  {name}: {status}")
        print(f"  (total models listed: {len(models)})")
    except Exception as exc:
        print(f"  models list failed: {exc}")
    print()

    print("=== ERROR: missing key ===")
    print(await test_missing_key())
    print()

    print("=== TEST 1: Resume generation (_generate_ai) ===")
    cleaned = CleanedProfile(
        name="Jane Smith",
        email="jane@example.com",
        career_level="Mid Level",
        education=[{"degree": "B.Tech", "institution": "IIT", "year": "2020"}],
        experience=[
            {
                "title": "Software Engineer",
                "company": "Acme",
                "from_date": "2021-01",
                "to_date": "Present",
                "responsibilities": "Built React dashboards",
            }
        ],
        projects=[],
        certifications=[],
        skills=["Python", "React", "SQL"],
        strengths=["Problem solving"],
        weblinks={},
        preferred_locations=[],
        preferred_sectors=[],
        warnings=[],
    )
    try:
        resume = await _generate_ai(cleaned, "software")
        print("  status: OK")
        print(
            f"  professional_summary: {resume.get('professional_summary', '')[:120]}..."
        )
        print(
            f"  skills.technical: {resume.get('skills', {}).get('technical', [])[:5]}"
        )
    except Exception as exc:
        print(f"  status: FAIL — {type(exc).__name__}: {exc}")
    print()

    print("=== TEST 2: ATS scoring (score_resume) ===")
    sample_resume = {
        "professional_summary": "Software engineer with Python and React experience.",
        "skills": {"technical": ["Python", "React", "SQL"], "soft": ["Communication"]},
        "experience": [
            {
                "title": "Engineer",
                "company": "Acme",
                "dates": "2021 – Present",
                "bullets": ["Improved API latency by 30%"],
            }
        ],
        "education": [{"degree": "B.Tech", "institution": "IIT", "year": "2020"}],
    }
    try:
        ats = await score_resume(sample_resume, "software")
        print("  status: OK")
        print(f"  overall_score: {ats.overall_score}")
        print(f"  breakdown: {ats.breakdown}")
        print(f"  issues_count: {len(ats.issues)}")
        print(f"  passed: {ats.passed}")
    except Exception as exc:
        print(f"  status: FAIL — {type(exc).__name__}: {exc}")
    print()

    print("=== TEST 3: Fitment rationale ===")
    print(
        "  NOT APPLICABLE — embeddings use EMBEDDING_API_KEY (OpenAI-compatible) or mock fallback; no Groq call."
    )
    print()

    print("=== TEST 4: PDF parse prompt (minimal generate_content) ===")
    try:
        parsed = await generate_content(
            'Extract name from: "John Doe, Software Engineer". Return JSON: {"name": "..."}',
            system_instruction="Return only valid JSON.",
            max_output_tokens=100,
        )
        print("  status: OK")
        print(f"  response: {json.dumps(parsed)}")
    except Exception as exc:
        print(f"  status: FAIL — {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
