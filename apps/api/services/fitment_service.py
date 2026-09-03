"""Stage-1 fitment — embedding similarity + skill heuristic; LLM rationales on ranked output."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import FitmentResult, JobPosting, Resume
from services.embedding_service import refresh_job_embedding
from services.fitment_rationale_service import generate_fitment_rationale, template_rationale


async def ensure_job_embedding(db: AsyncSession, job: JobPosting) -> list[float]:
    if job.embedding is not None:
        return list(job.embedding)
    await refresh_job_embedding(db, job)
    return list(job.embedding)


async def compute_fitment(db: AsyncSession, job: JobPosting, limit: int = 20) -> list[FitmentResult]:
    """Rank candidates by resume↔job embedding distance; skill-overlap heuristic fallback."""
    await ensure_job_embedding(db, job)

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
        job_skills = list(job.required_skills or [])
        for row in rows:
            distance = float(row["distance"] or 0)
            score = max(40.0, min(98.0, 100.0 - distance * 25))
            rationale = template_rationale(job_skills)
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
            template_rationale(list(job.required_skills or []), list(overlap))
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
    """Compute fitment; upgrade rationales via Groq when configured."""
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

        rationale, source = await generate_fitment_rationale(
            job_title=job.title,
            job_department=job.department,
            job_skills=list(job.required_skills or []),
            candidate_name=display_name or name,
            candidate_title=(profile.preferred_sectors or [None])[0] if profile else None,
            candidate_skills=skills,
            score=fr.score,
        )
        fr.rationale = rationale
        out.append(
            FitmentCandidateOut(
                candidate_id=fr.candidate_id,
                name=display_name or name,
                title=(profile.preferred_sectors or [None])[0] if profile else None,
                score=fr.score,
                rationale=rationale,
                rationale_source=source,
                skills=skills,
                location=(profile.preferred_locations or [None])[0] if profile else None,
            )
        )
    await db.flush()
    out.sort(key=lambda x: x.score, reverse=True)
    return out
