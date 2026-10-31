"""Embedding helpers — OpenAI embeddings with validation, no mock fallback."""

from __future__ import annotations

import logging
import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models import EmbeddingStatus, JobPosting, Resume
from services.embedding_client import EmbeddingServiceError, fetch_embedding

logger = logging.getLogger(__name__)
settings = get_settings()

# OpenAI text-embedding-3-small produces 512-dimensional vectors
EMBED_DIM = 512
EPSILON = 1e-8  # Minimum vector norm to reject all-zero vectors


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


async def embed_text(text: str) -> list[float]:
    """Generate a real 512-dimensional embedding via OpenAI, or raise EmbeddingError.
    
    Never returns fake/mock vectors. On API failure, raises EmbeddingError with
    descriptive message. Caller must handle the error and decide whether to:
    - Store NULL embedding with status='failed'
    - Retry later
    - Use fallback ranking method
    """
    if not settings.embedding_api_key:
        raise EmbeddingError(
            "Embedding API key not configured. "
            "Set EMBEDDING_API_KEY in .env to use real embeddings."
        )
    
    try:
        vector = await fetch_embedding(text)
    except EmbeddingServiceError as exc:
        logger.error("Embedding API failed: %s", exc)
        raise EmbeddingError(f"Embedding API unavailable: {str(exc)}") from exc
    
    # Validate the returned vector
    try:
        validate_embedding(vector, text)
    except EmbeddingError as exc:
        logger.error("Embedding validation failed: %s", exc)
        raise
    
    return vector


def build_job_embedding_text(job: JobPosting) -> str:
    """Build searchable text for job embedding from title, skills, description, etc."""
    return " ".join(
        filter(
            None,
            [
                job.title,
                job.department,
                job.job_role,
                job.job_level,
                job.description,
                job.experience_range,
                " ".join(job.required_skills or []),
            ],
        )
    )


def build_resume_embedding_text(resume: Resume) -> str:
    """Build searchable text for resume embedding from skills, summary, mapping notes."""
    content = resume.content or {}
    highlighted = content.get("highlightedSkills") or content.get("skills") or []
    skills = (
        " ".join(str(s) for s in highlighted)
        if isinstance(highlighted, list)
        else str(highlighted)
    )
    summary = content.get("summary") or ""
    mapping = content.get("mappingNotes") or content.get("mapping_notes") or ""
    return f"{resume.target_vertical or ''} {skills} {summary} {mapping}".strip()


async def refresh_job_embedding(db: AsyncSession, job: JobPosting) -> None:
    """Re-embed job posting when title/description/skills change.
    
    On failure: stores NULL embedding and sets status='failed' (caller must surface this).
    On success: stores vector and sets status='scored'.
    """
    embedding_text = build_job_embedding_text(job) or job.title
    
    try:
        job.embedding = await embed_text(embedding_text)
        job.embedding_status = EmbeddingStatus.scored.value
        job.embedding_model = "text-embedding-3-small"
    except EmbeddingError as exc:
        logger.warning("Job embedding failed for job %s: %s", job.id, exc)
        job.embedding = None
        job.embedding_status = EmbeddingStatus.failed.value
    
    await db.flush()


async def refresh_resume_embeddings_for_candidate(
    db: AsyncSession, candidate_id: UUID
) -> int:
    """Re-embed all resumes for a candidate after profile update.
    
    Returns count of successfully embedded resumes.
    Failed embeddings are stored as NULL with status='failed'.
    """
    resumes = (
        (await db.execute(select(Resume).where(Resume.candidate_id == candidate_id)))
        .scalars()
        .all()
    )
    
    success_count = 0
    for resume in resumes:
        embedding_text = build_resume_embedding_text(resume) or "resume"
        
        try:
            resume.embedding = await embed_text(embedding_text)
            resume.embedding_status = EmbeddingStatus.scored.value
            resume.embedding_model = "text-embedding-3-small"
            success_count += 1
        except EmbeddingError as exc:
            logger.warning("Resume embedding failed for resume %s: %s", resume.id, exc)
            resume.embedding = None
            resume.embedding_status = EmbeddingStatus.failed.value
    
    if resumes:
        await db.flush()
    
    return success_count
