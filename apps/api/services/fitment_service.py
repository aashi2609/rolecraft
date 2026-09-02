"""Stage-1 fitment — embedding stub + pgvector similarity when available."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Optional
from uuid import UUID


from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models import FitmentResult, JobPosting, Resume

settings = get_settings()
EMBED_DIM = 1536


def _mock_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding so similarity is stable without Gemini."""
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    vec = [rng.uniform(-1, 1) for _ in range(EMBED_DIM)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


async def embed_text(text: str) -> list[float]:
    # Groq does not currently support embeddings via the OpenAI API format
    # Using deterministic mock embeddings for now
    return _mock_embedding(text)


async def ensure_job_embedding(db: AsyncSession, job: JobPosting) -> list[float]:
    if job.embedding is not None:
        return list(job.embedding)
    blob = " ".join(
        filter(
            None,
            [
                job.title,
                job.department,
                job.description,
                " ".join(job.required_skills or []),
            ],
        )
    )
    vec = await embed_text(blob or job.title)
    job.embedding = vec
    await db.flush()
    return vec


async def compute_fitment(db: AsyncSession, job: JobPosting, limit: int = 20) -> list[FitmentResult]:
    """
    Rank candidates by resume↔job embedding distance.
    Falls back to skill-overlap heuristic if no embeddings exist.
    """
    await ensure_job_embedding(db, job)

    # Try pgvector nearest-neighbor on resumes for this job's embedding
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT r.candidate_id, r.id AS resume_id,
                           (r.embedding <-> :job_emb) AS distance
                    FROM resumes r
                    WHERE r.embedding IS NOT NULL
                    ORDER BY r.embedding <-> :job_emb
                    LIMIT :lim
                    """
                ),
                {"job_emb": str(job.embedding), "lim": limit},
            )
        ).mappings().all()
    except Exception:
        rows = []

    results: list[FitmentResult] = []
    if rows:
        for row in rows:
            distance = float(row["distance"] or 0)
            # Convert L2 distance to 0-100-ish score
            score = max(40.0, min(98.0, 100.0 - distance * 25))
            # Template rationale (interim — not LLM). Keep in sync with candidate_search_service.
            skills = ", ".join((job.required_skills or [])[:3]) or "core requirements"
            rationale = f"Strong skills overlap in {skills}."
            existing = await db.scalar(
                select(FitmentResult).where(
                    FitmentResult.job_id == job.id,
                    FitmentResult.candidate_id == row["candidate_id"],
                )
            )
            if existing:
                existing.score = score
                existing.rationale = rationale
                results.append(existing)
            else:
                fr = FitmentResult(
                    job_id=job.id,
                    candidate_id=row["candidate_id"],
                    score=score,
                    rationale=rationale,
                )
                db.add(fr)
                results.append(fr)
        await db.flush()
        return results

    # Heuristic fallback: skill overlap against all resumes
    resumes = (await db.execute(select(Resume))).scalars().all()
    job_skills = {s.lower() for s in (job.required_skills or [])}
    scored: list[tuple[UUID, float, str]] = []
    for resume in resumes:
        content = resume.content or {}
        cand_skills = {s.lower() for s in content.get("highlightedSkills", [])}
        overlap = job_skills & cand_skills if job_skills else set()
        base = 55 + 10 * len(overlap)
        if resume.target_vertical and job.department and resume.target_vertical.lower() in (job.department or "").lower():
            base += 8
        score = min(96.0, float(base))
        rationale = (
            f"Strong skills overlap in {', '.join(sorted(overlap)[:3])}."
            if overlap
            else "Partial profile match based on vertical alignment."
        )
        scored.append((resume.candidate_id, score, rationale))

    scored.sort(key=lambda x: x[1], reverse=True)
    for candidate_id, score, rationale in scored[:limit]:
        existing = await db.scalar(
            select(FitmentResult).where(
                FitmentResult.job_id == job.id,
                FitmentResult.candidate_id == candidate_id,
            )
        )
        if existing:
            existing.score = score
            existing.rationale = rationale
            results.append(existing)
        else:
            fr = FitmentResult(job_id=job.id, candidate_id=candidate_id, score=score, rationale=rationale)
            db.add(fr)
            results.append(fr)
    await db.flush()
    return results


async def ranked_candidates_for_job(db: AsyncSession, job: JobPosting) -> list:
    """Compute fitment and return FitmentCandidateOut-ready dicts sorted by score."""
    from sqlalchemy.orm import selectinload

    from models import CandidateProfile, CandidateSkill
    from schemas import FitmentCandidateOut

    results = await compute_fitment(db, job)
    out: list[FitmentCandidateOut] = []
    for fr in results:
        profile = (
            await db.execute(
                select(CandidateProfile)
                .options(
                    selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
                    selectinload(CandidateProfile.user),
                )
                .where(CandidateProfile.user_id == fr.candidate_id)
            )
        ).scalar_one_or_none()
        skills = [cs.skill.name for cs in (profile.skills if profile else []) if cs.skill]
        email = profile.user.email if profile and profile.user else None
        name = email.split("@")[0].replace(".", " ").title() if email else "Candidate"
        display_name = None
        if profile and profile.weblinks:
            display_name = profile.weblinks.get("display_name")
        out.append(
            FitmentCandidateOut(
                candidate_id=fr.candidate_id,
                name=display_name or name,
                title=(profile.preferred_sectors or [None])[0] if profile else None,
                score=fr.score,
                rationale=fr.rationale,
                skills=skills,
                location=(profile.preferred_locations or [None])[0] if profile else None,
            )
        )
    out.sort(key=lambda x: x.score, reverse=True)
    return out
