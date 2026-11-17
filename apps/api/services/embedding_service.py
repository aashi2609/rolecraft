"""Embedding helpers — OpenAI embeddings with validation, no mock fallback."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.embedding_config import (
    EMBEDDING_DIM,
    EMBEDDING_INPUT_VERSION,
    EMBEDDING_MODEL,
)
from models import EmbeddingStatus, JobPosting, Resume
from services.embedding_client import EmbeddingServiceError, fetch_embeddings

logger = logging.getLogger(__name__)
settings = get_settings()

EMBED_DIM = EMBEDDING_DIM
EPSILON = 1e-8  # Minimum vector norm to reject all-zero vectors
MAX_EMBED_CHARS = 24000  # ~6k tokens, safely under model limits


class EmbeddingError(Exception):
    """Raised when embedding cannot be generated or is invalid."""


def validate_embedding(vector: list[float], text: str) -> None:
    """Validate embedding vector: correct dimension, finite, non-zero norm, non-empty text.

    Raises EmbeddingError if validation fails.
    """
    if not text or not text.strip():
        raise EmbeddingError("Cannot embed empty text")

    if not isinstance(vector, list):
        raise EmbeddingError(f"Embedding must be a list, got {type(vector)}")

    if len(vector) != EMBED_DIM:
        raise EmbeddingError(
            f"Embedding dimension mismatch: expected {EMBED_DIM}, got {len(vector)}"
        )

    # Check all values are finite (not NaN or inf)
    for i, v in enumerate(vector):
        if not isinstance(v, (int, float)):
            raise EmbeddingError(f"Embedding[{i}] is not numeric: {type(v)}")
        if not math.isfinite(v):
            raise EmbeddingError(f"Embedding[{i}] is not finite: {v}")

    # Check vector norm is above epsilon (reject all-zero vectors)
    norm = math.sqrt(sum(x * x for x in vector))
    if norm < EPSILON:
        raise EmbeddingError(f"Embedding vector is all-zero (norm={norm})")


def _cap(text: str) -> str:
    return text[:MAX_EMBED_CHARS]


def _sorted_skills(skills: Any) -> list[str]:
    if not skills:
        return []
    if isinstance(skills, str):
        return sorted(s.strip() for s in skills.split(",") if s.strip())
    return sorted(str(s).strip() for s in skills if str(s).strip())


def content_hash(text: str) -> str:
    """sha256 of the exact text sent to the embedding provider."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_job_embedding_text(job: JobPosting) -> str:
    """Deterministic, PII-free text for job embeddings (v{EMBEDDING_INPUT_VERSION})."""
    parts = [
        f"title: {job.title or ''}",
        f"role: {job.job_role or ''}",
        f"level: {job.job_level or ''}",
        f"department: {job.department or ''}",
        f"employment_type: {job.employment_type or ''}",
        f"experience_range: {job.experience_range or ''}",
        f"location: {job.location or ''}",
        f"skills: {', '.join(_sorted_skills(job.required_skills))}",
        f"description: {job.description or ''}",
        f"responsibilities: {job.responsibilities or ''}",
        f"requirements: {job.requirements or ''}",
    ]
    return _cap("\n".join(p for p in parts if not p.endswith(": ")))


def _resume_content(resume: Resume) -> dict:
    return resume.content or {}


def build_resume_embedding_text(resume: Resume, profile: Any = None) -> str:
    """Deterministic, PII-free text for resume embeddings.

    Includes role/vertical, skills, titles, employers, education field,
    certifications, projects. EXCLUDES name/email/phone/address/DOB/gender/
    marital/religion/family/salary/photo/weblinks.
    """
    content = _resume_content(resume)
    exp = content.get("experience") or []
    if not isinstance(exp, list):
        exp = []
    jobs = []
    for e in exp:
        if not isinstance(e, dict):
            continue
        jobs.append(
            " | ".join(
                str(e.get(k) or "")
                for k in ("title", "company", "role", "responsibilities")
            ).strip(" |")
        )
    education = content.get("education") or []
    if not isinstance(education, list):
        education = []
    edu_fields = [
        str(e.get("field") or e.get("degree") or "")
        for e in education
        if isinstance(e, dict)
    ]
    skills = _sorted_skills(
        content.get("highlightedSkills") or content.get("skills") or []
    )
    projects = content.get("projects") or []
    project_text = " ".join(
        str(p.get("name") or p.get("description") or "")
        for p in projects
        if isinstance(p, dict)
    )
    certifications = content.get("certifications") or []
    cert_text = " ".join(
        str(c.get("name") or c) if isinstance(c, dict) else str(c)
        for c in certifications
    )
    profile_bits = ""
    if profile is not None:
        profile_bits = " ".join(
            str(x or "")
            for x in (
                getattr(profile, "target_role", None),
                getattr(profile, "headline", None),
            )
        )
    parts = [
        f"input_version: {EMBEDDING_INPUT_VERSION}",
        f"target_vertical: {resume.target_vertical or ''}",
        f"profile: {profile_bits}",
        f"skills: {', '.join(skills)}",
        f"summary: {content.get('summary') or content.get('professional_summary') or ''}",
        f"experience: {' ;; '.join(j for j in jobs if j)}",
        f"education: {'; '.join(edu_fields)}",
        f"certifications: {cert_text}",
        f"projects: {project_text}",
    ]
    return _cap("\n".join(p for p in parts if not p.endswith(": ")))


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch; validates every vector. Raises EmbeddingError."""
    if not settings.embedding_api_key:
        raise EmbeddingError(
            "Embedding API key not configured. "
            "Set EMBEDDING_API_KEY in .env to use real embeddings."
        )
    try:
        vectors = await fetch_embeddings(texts)
    except EmbeddingServiceError as exc:
        logger.error("Embedding API failed: %s", exc)
        raise EmbeddingError(f"Embedding API unavailable: {exc}") from exc
    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"Embedding count mismatch: expected {len(texts)}, got {len(vectors)}"
        )
    for text, vector in zip(texts, vectors):
        validate_embedding(vector, text)
    return vectors


async def embed_text(text: str) -> list[float]:
    """Single-text wrapper; raises EmbeddingError, never returns placeholders."""
    vectors = await embed_texts([text])
    return vectors[0]


async def refresh_job_embedding(db: AsyncSession, job: JobPosting) -> None:
    """Re-embed job posting; stores vector+model+hash on success,
    NULL+'failed' on EmbeddingError. Caller must surface failure.
    Skips the API call entirely when the built text hash is unchanged."""
    embedding_text = build_job_embedding_text(job) or (job.title or "")
    new_hash = content_hash(embedding_text)
    if (
        job.embedding_source_hash == new_hash
        and job.embedding_status == EmbeddingStatus.scored.value
        and job.embedding_model == EMBEDDING_MODEL
    ):
        return
    try:
        vector = await embed_text(embedding_text)
        job.embedding = vector
        job.embedding_status = EmbeddingStatus.scored.value
        job.embedding_model = EMBEDDING_MODEL
        job.embedding_source_hash = new_hash
    except EmbeddingError as exc:
        logger.warning("Job embedding failed for job %s: %s", job.id, type(exc).__name__)
        job.embedding = None
        job.embedding_status = EmbeddingStatus.failed.value
    await db.flush()


async def refresh_job_embedding_bg(job_id: UUID) -> None:
    """Background-task entry point: own short session, never fails the request."""
    from core.database import AsyncSessionLocal
    from models import JobPosting as _Job

    try:
        async with AsyncSessionLocal() as db:
            job = await db.get(_Job, job_id)
            if job is None:
                return
            await refresh_job_embedding(db, job)
            await db.commit()
    except Exception as exc:  # provider/DB errors must not propagate to caller
        logger.warning("Background job embedding failed: %s", type(exc).__name__)


async def refresh_candidate_embeddings_bg(candidate_id: UUID) -> None:
    """Background-task entry point: own short session, never fails the request."""
    try:
        from core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await refresh_resume_embeddings_for_candidate(db, candidate_id)
            await db.commit()
    except Exception as exc:
        logger.warning(
            "Background resume embedding refresh failed: %s", type(exc).__name__
        )


async def refresh_resume_embeddings_for_candidate(
    db: AsyncSession, candidate_id: UUID
) -> int:
    """Re-embed all resumes for a candidate. Returns count of successes."""
    resumes = (
        (await db.execute(select(Resume).where(Resume.candidate_id == candidate_id)))
        .scalars()
        .all()
    )
    success_count = 0
    for resume in resumes:
        embedding_text = build_resume_embedding_text(resume) or "resume"
        new_hash = content_hash(embedding_text)
        if (
            resume.embedding_source_hash == new_hash
            and resume.embedding_status == EmbeddingStatus.scored.value
            and resume.embedding_model == EMBEDDING_MODEL
        ):
            continue
        try:
            resume.embedding = await embed_text(embedding_text)
            resume.embedding_status = EmbeddingStatus.scored.value
            resume.embedding_model = EMBEDDING_MODEL
            resume.embedding_source_hash = new_hash
            success_count += 1
        except EmbeddingError as exc:
            logger.warning(
                "Resume embedding failed for resume %s: %s", resume.id, type(exc).__name__
            )
            resume.embedding = None
            resume.embedding_status = EmbeddingStatus.failed.value
    if resumes:
        await db.flush()
    return success_count
