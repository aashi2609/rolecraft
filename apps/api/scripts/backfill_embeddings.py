#!/usr/bin/env python
"""Backfill resume/job embeddings (Step F).

Dry-run by DEFAULT. Real run requires --apply. Refuses the primary DB
unless --target primary is passed AND the user confirms interactively.

Never logs resume text, vectors, or API keys.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select, text

from core.database import AsyncSessionLocal, engine
from core.embedding_config import EMBEDDING_MODEL
from models import EmbeddingStatus, JobPosting, Resume
from services.embedding_service import (
    EmbeddingError,
    build_job_embedding_text,
    build_resume_embedding_text,
    content_hash,
    embed_texts,
)

PRIMARY_HOST_HINTS = ("fragrant-salad",)  # primary Neon endpoint id fragment

# NOTE: compute_fitment uses the L2 distance operator `<->`. If an ANN index is
# ever added on resumes.embedding / job_postings.embedding it MUST be created
# with the `vector_l2_ops` operator class (USING hnsw (embedding vector_l2_ops))
# to match `<->`. Do not use cosine (<=>) or inner-product (<#>) classes.


def _db_label() -> str:
    url = str(engine.url)
    p = urlparse(url.replace("+asyncpg", ""))
    return f"{p.hostname}/{p.path.lstrip('/')}"


def _is_primary() -> bool:
    host = (engine.url.host or "").lower()
    return any(h in host for h in PRIMARY_HOST_HINTS)


async def _iter_candidates(db, table, batch_size, limit, retry_failed):
    """Keyset-paginate rows so per-batch commits don't kill a server-side cursor."""
    model = Resume if table == "resumes" else JobPosting
    last_id = None
    produced = 0
    while True:
        stmt = select(model).order_by(model.id).limit(batch_size)
        if last_id is not None:
            stmt = stmt.where(model.id > last_id)
        rows = (await db.execute(stmt)).scalars().all()
        if not rows:
            return
        last_id = rows[-1].id
        needed = [r for r in rows if await _needs_embedding(r, table, db)]
        for i in range(0, len(needed), batch_size):
            yield needed[i : i + batch_size]
            produced += len(needed[i : i + batch_size])
            if limit and produced >= limit:
                return


async def _needs_embedding(row, table, db) -> bool:
    """True when row is missing/stale vs freshly built text hash."""
    if row.embedding is None or row.embedding_status != EmbeddingStatus.scored.value:
        return True
    if row.embedding_model != EMBEDDING_MODEL:
        return True
    if table == "resumes":
        text_ = build_resume_embedding_text(row) or "resume"
    else:
        text_ = build_job_embedding_text(row) or (row.title or "")
    return row.embedding_source_hash != content_hash(text_)


async def run(args) -> int:
    label = _db_label()
    print(f"Target DB: {label}")
    if _is_primary() and not args.target_primary:
        print(
            "REFUSING: this looks like the primary database. "
            "Pass --target primary and confirm to proceed."
        )
        return 2
    if _is_primary() and args.target_primary:
        confirm = input("Type 'yes' to run the backfill on PRIMARY: ").strip()
        if confirm != "yes":
            print("Aborted.")
            return 2

    tables = ["resumes", "job_postings"] if args.table == "all" else [args.table]
    total_done = total_skip = total_fail = 0
    api_requests = 0
    # Hard ceiling on provider calls per run — protects against runaway cost.
    max_requests = getattr(args, "max_requests", None) or 10_000

    async with AsyncSessionLocal() as db:
        for table in tables:
            model = Resume if table == "resumes" else JobPosting
            # selection count for dry-run report
            count = await db.scalar(
                select(text("count(*)")).select_from(model).where(model.embedding.is_(None))
            )
            print(f"[{table}] rows with NULL embedding: {count}")

            processed = 0
            async for batch in _iter_candidates(
                db, table, args.batch_size, args.max_rows, args.retry_failed
            ):
                if args.max_rows and processed >= args.max_rows:
                    break
                batch = batch[: args.batch_size]
                # filter to actually-needed rows
                needed = []
                for row in batch:
                    try:
                        if await _needs_embedding(row, table, db):
                            needed.append(row)
                        else:
                            total_skip += 1
                    except Exception:
                        total_skip += 1
                if not needed:
                    continue

                texts = []
                for row in needed:
                    texts.append(
                        build_resume_embedding_text(row) or "resume"
                        if table == "resumes"
                        else build_job_embedding_text(row) or (row.title or "")
                    )
                est_tokens = sum(len(t) // 4 for t in texts)
                print(
                    f"[{table}] batch of {len(needed)} "
                    f"(~{est_tokens} tokens, est cost ~${est_tokens * 0.02 / 1e6:.6f} "
                    "@ $0.02/1M tok)"
                )
                if args.dry_run or not args.apply:
                    total_done += len(needed)
                    processed += len(needed)
                    continue

                if api_requests >= max_requests:
                    print(f"Request ceiling reached ({max_requests}); stopping.")
                    break
                try:
                    vectors = await embed_texts(texts)
                    api_requests += 1
                except EmbeddingError as exc:
                    # whole-batch provider failure: mark rows failed, keep going
                    for row in needed:
                        row.embedding = None
                        row.embedding_status = EmbeddingStatus.failed.value
                        total_fail += 1
                    await db.commit()
                    print(f"[{table}] batch failed: {type(exc).__name__}")
                    continue

                ok = 0
                for row, vec, txt in zip(needed, vectors, texts):
                    try:
                        row.embedding = vec
                        row.embedding_status = EmbeddingStatus.scored.value
                        row.embedding_model = EMBEDDING_MODEL
                        row.embedding_source_hash = content_hash(txt)
                        ok += 1
                    except Exception:
                        row.embedding = None
                        row.embedding_status = EmbeddingStatus.failed.value
                        total_fail += 1
                await db.commit()
                total_done += ok
                processed += len(needed)
                print(f"[{table}] progress: done={total_done} skip={total_skip} fail={total_fail}")

    print(
        f"SUMMARY table={args.table} done={total_done} skipped={total_skip} "
        f"failed={total_fail} dry_run={args.dry_run or not args.apply}"
    )
    return 1 if total_fail else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Embedding backfill (dry-run default)")
    ap.add_argument("--table", choices=["resumes", "jobs", "all"], default="all")
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--limit", type=int, default=None, help="max rows per table")
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true", help="actually write (disables dry-run)")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--target", choices=["test", "primary"], default="test")
    ap.add_argument(
        "--max-requests",
        type=int,
        default=10_000,
        help="hard ceiling on embedding API calls this run",
    )
    args = ap.parse_args()
    args.dry_run = not args.apply
    args.target_primary = args.target == "primary"
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
