"""Embedding helpers — OpenAI-compatible API when configured, mock fallback otherwise."""

from __future__ import annotations

import hashlib
import logging
import math
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models import JobPosting, Resume
from services.embedding_client import EmbeddingServiceError, fetch_embedding

logger = logging.getLogger(__name__)
settings = get_settings()

EMBED_DIM = 1536


def mock_embedding(text: str) -> list[float]:
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    vec = [rng.uniform(-1, 1) for _ in range(EMBED_DIM)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


async def embed_text(text: str) -> list[float]:
    # Backup mode: never call the embedding provider (avoids long hangs / Failed to fetch).
    if settings.force_deterministic_resumes:
        return mock_embedding(text)
    if settings.embedding_api_key:
        try:
            return await fetch_embedding(text)
        except EmbeddingServiceError as exc:
            logger.warning("Embedding API failed, using mock fallback: %s", exc)
    return mock_embedding(text)


def build_job_embedding_text(job: JobPosting) -> str:
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
    job.embedding = await embed_text(build_job_embedding_text(job) or job.title)
    await db.flush()


async def refresh_resume_embeddings_for_candidate(
    db: AsyncSession, candidate_id: UUID
) -> int:
    resumes = (
        (await db.execute(select(Resume).where(Resume.candidate_id == candidate_id)))
        .scalars()
        .all()
    )
    for resume in resumes:
        resume.embedding = await embed_text(
            build_resume_embedding_text(resume) or "resume"
        )
    if resumes:
        await db.flush()
    return len(resumes)
