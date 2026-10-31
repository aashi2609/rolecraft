#!/usr/bin/env python3
"""
Step 5B Backfill: Re-embed all resumes and jobs with real OpenAI vectors.

This script runs AFTER the database migration (j1k2l3m4n5o6).
- All existing embeddings are set to NULL by the migration
- This script re-embeds them with text-embedding-3-small (512 dims)
- Tracks embedding_status and embedding_model for each record
- Reports success/failure counts and sample cosine distances

Usage:
  python scripts/backfill_embeddings_step5b.py

Set TEST_DATABASE_URL or DATABASE_URL before running.
"""

import asyncio
import logging
import sys
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def backfill_resume_embeddings(db: AsyncSession) -> dict:
    """Re-embed all resumes. Return stats dict."""
    from models import Resume, EmbeddingStatus
    from services.embedding_service import (
        build_resume_embedding_text,
        embed_text,
        EmbeddingError,
    )
    
    logger.info("Starting resume backfill...")
    
    # Get all resumes
    resumes = (await db.execute(select(Resume))).scalars().all()
    total = len(resumes)
    logger.info(f"Found {total} resumes to backfill")
    
    success_count = 0
    failed_count = 0
    sample_vectors = []  # For spot-checking
    
    for i, resume in enumerate(resumes, 1):
        try:
            text = build_resume_embedding_text(resume)
            vector = await embed_text(text)
            
            resume.embedding = vector
            resume.embedding_status = EmbeddingStatus.scored.value
            resume.embedding_model = "text-embedding-3-small"
            
            success_count += 1
            
            # Store sample for verification
            if len(sample_vectors) < 3:
                sample_vectors.append({
                    "resume_id": str(resume.id),
                    "vertical": resume.target_vertical,
                    "embedding_len": len(vector),
                    "first_5_dims": vector[:5],
                })
            
            if i % 10 == 0:
                logger.info(f"  {i}/{total} resumes embedded")
        
        except EmbeddingError as exc:
            logger.warning(f"Resume {resume.id} embedding failed: {exc}")
            resume.embedding = None
            resume.embedding_status = EmbeddingStatus.failed.value
            failed_count += 1
        
        except Exception as exc:
            logger.error(f"Resume {resume.id} unexpected error: {exc}")
            resume.embedding = None
            resume.embedding_status = EmbeddingStatus.failed.value
            failed_count += 1
    
    await db.flush()
    await db.commit()
    
    logger.info(f"Resume backfill complete: {success_count} success, {failed_count} failed")
    
    return {
        "type": "resumes",
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "samples": sample_vectors,
    }


async def backfill_job_embeddings(db: AsyncSession) -> dict:
    """Re-embed all jobs. Return stats dict."""
    from models import JobPosting, EmbeddingStatus
    from services.embedding_service import (
        build_job_embedding_text,
        embed_text,
        EmbeddingError,
    )
    
    logger.info("Starting job backfill...")
    
    # Get all jobs
    jobs = (await db.execute(select(JobPosting))).scalars().all()
    total = len(jobs)
    logger.info(f"Found {total} jobs to backfill")
    
    success_count = 0
    failed_count = 0
    sample_vectors = []
    
    for i, job in enumerate(jobs, 1):
        try:
            text = build_job_embedding_text(job) or job.title
            vector = await embed_text(text)
            
            job.embedding = vector
            job.embedding_status = EmbeddingStatus.scored.value
            job.embedding_model = "text-embedding-3-small"
            
            success_count += 1
            
            if len(sample_vectors) < 3:
                sample_vectors.append({
                    "job_id": str(job.id),
                    "title": job.title,
                    "embedding_len": len(vector),
                    "first_5_dims": vector[:5],
                })
            
            if i % 10 == 0:
                logger.info(f"  {i}/{total} jobs embedded")
        
        except EmbeddingError as exc:
            logger.warning(f"Job {job.id} embedding failed: {exc}")
            job.embedding = None
            job.embedding_status = EmbeddingStatus.failed.value
            failed_count += 1
        
        except Exception as exc:
            logger.error(f"Job {job.id} unexpected error: {exc}")
            job.embedding = None
            job.embedding_status = EmbeddingStatus.failed.value
            failed_count += 1
    
    await db.flush()
    await db.commit()
    
    logger.info(f"Job backfill complete: {success_count} success, {failed_count} failed")
    
    return {
        "type": "jobs",
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "samples": sample_vectors,
    }


async def verify_cosine_similarity(db: AsyncSession) -> None:
    """Spot-check: compute cosine distance between two clearly different resumes."""
    from models import Resume
    import math
    
    logger.info("Verifying cosine similarity between sample resumes...")
    
    # Get 2 resumes with embeddings
    resumes = (
        await db.execute(
            select(Resume)
            .where(Resume.embedding.isnot(None))
            .limit(2)
        )
    ).scalars().all()
    
    if len(resumes) < 2:
        logger.info("Not enough resumes with embeddings for verification")
        return
    
    r1, r2 = resumes[0], resumes[1]
    
    # Compute cosine distance
    v1 = list(r1.embedding) if r1.embedding else []
    v2 = list(r2.embedding) if r2.embedding else []
    
    if not v1 or not v2:
        logger.warning("Sample resumes have NULL embeddings")
        return
    
    # Cosine similarity = dot(v1, v2) / (norm(v1) * norm(v2))
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(x ** 2 for x in v1))
    norm2 = math.sqrt(sum(x ** 2 for x in v2))
    
    if norm1 == 0 or norm2 == 0:
        logger.warning("Sample embeddings have zero norm")
        return
    
    cosine_sim = dot_product / (norm1 * norm2)
    cosine_dist = 1 - cosine_sim
    
    logger.info(f"Sample resume 1: {r1.target_vertical}")
    logger.info(f"Sample resume 2: {r2.target_vertical}")
    logger.info(f"Cosine distance: {cosine_dist:.4f} (0=identical, 2=opposite)")
    
    if cosine_dist < 0.1:
        logger.warning("Cosine distance is very small - may indicate similar resumes or fake embeddings")
    elif cosine_dist > 1.8:
        logger.info("Cosine distance is large - good sign of different embeddings")


async def main():
    """Run the backfill."""
    from core.database import get_db
    
    logger.info("=" * 70)
    logger.info("Step 5B Embedding Backfill")
    logger.info("=" * 70)
    
    try:
        async for db in get_db():
            logger.info(f"Started at {datetime.now().isoformat()}")
            
            resume_stats = await backfill_resume_embeddings(db)
            job_stats = await backfill_job_embeddings(db)
            await verify_cosine_similarity(db)
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("BACKFILL SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Resumes: {resume_stats['success']}/{resume_stats['total']} succeeded")
            logger.info(f"Jobs:    {job_stats['success']}/{job_stats['total']} succeeded")
            
            if resume_stats['samples']:
                logger.info("\nSample Resume Embeddings:")
                for sample in resume_stats['samples']:
                    logger.info(f"  {sample['resume_id'][:8]}... ({sample['vertical']}): {sample['first_5_dims'][:3]}")
            
            if job_stats['samples']:
                logger.info("\nSample Job Embeddings:")
                for sample in job_stats['samples']:
                    logger.info(f"  {sample['job_id'][:8]}... ({sample['title'][:30]}): {sample['first_5_dims'][:3]}")
            
            logger.info("")
            logger.info(f"Completed at {datetime.now().isoformat()}")
            logger.info("=" * 70)
            
            break
    
    except Exception as exc:
        logger.error(f"Backfill failed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
