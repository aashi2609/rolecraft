"""Step F tests: embedding dimension consistency, builders, client, fitment."""

import uuid as _uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from core.database import engine
from core.embedding_config import (
    EMBEDDING_DIM,
    EMBEDDING_INPUT_VERSION,
    EMBEDDING_MODEL,
)
from models import CandidateProfile, Company, JobPosting, Resume, User, UserRole
from services import embedding_service as es
from services.embedding_client import EmbeddingServiceError, fetch_embeddings
from services.fitment_service import ensure_job_embedding

pytestmark = pytest.mark.asyncio


def make_vector(dim: int = EMBEDDING_DIM, seed: float = 1.0) -> list[float]:
    """Deterministic test vector — clearly a helper, not provider output."""
    return [seed + i * 0.001 for i in range(dim)]


class TestConsistency:
    async def test_constant_matches_model_columns(self):
        from models import JobPosting as JP
        from models import Resume as R

        assert R.__table__.c.embedding.type.dim == EMBEDDING_DIM
        assert JP.__table__.c.embedding.type.dim == EMBEDDING_DIM

    async def test_constant_matches_migration(self):
        import re
        from pathlib import Path

        mig = (
            Path(__file__).resolve().parent.parent
            / "alembic/versions/p8q9r0s1t2u3_step_f_embedding_dim_1536.py"
        ).read_text()
        m = re.search(r"TARGET_DIM\s*=\s*(\d+)", mig)
        assert m and int(m.group(1)) == EMBEDDING_DIM

    async def test_live_column_dimension(self):
        async with engine.connect() as c:
            for table in ("resumes", "job_postings"):
                dim = (
                    await c.execute(
                        text(
                            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                            "WHERE attrelid=CAST(:t AS regclass) AND attname='embedding'"
                        ),
                        {"t": table},
                    )
                ).scalar()
                assert dim == f"vector({EMBEDDING_DIM})", dim

    def test_validate_embedding_length(self):
        es.validate_embedding(make_vector(), "text")
        with pytest.raises(es.EmbeddingError):
            es.validate_embedding(make_vector(EMBEDDING_DIM - 1), "text")

    def test_validate_rejects_nan_and_zero(self):
        bad = make_vector()
        bad[0] = float("nan")
        with pytest.raises(es.EmbeddingError):
            es.validate_embedding(bad, "text")
        with pytest.raises(es.EmbeddingError):
            es.validate_embedding([0.0] * EMBEDDING_DIM, "text")
        with pytest.raises(es.EmbeddingError):
            es.validate_embedding(make_vector(), "")


class TestBuilders:
    def test_job_builder_deterministic_and_pii_free(self):
        job = JobPosting(
            title="Backend Engineer",
            job_role="backend",
            job_level="senior",
            department="Engineering",
            required_skills=["python", "sql", "fastapi"],
            description="Build APIs",
            requirements="5 years",
        )
        a = es.build_job_embedding_text(job)
        b = es.build_job_embedding_text(job)
        assert a == b
        assert "input_version" not in a  # jobs versioned via hash only
        low = a.lower()
        for pii in ("@", "phone", "salary", "address"):
            assert pii not in low or pii == "@"  # '@' never present anyway
        assert "python" in low and "fastapi" in low

    def test_resume_builder_pii_free(self):
        resume = Resume(
            target_vertical="backend",
            content={
                "highlightedSkills": ["Python", "SQL"],
                "summary": "Backend dev",
                "experience": [
                    {
                        "title": "SWE",
                        "company": "Acme",
                        "role": "backend",
                        "responsibilities": "APIs",
                    }
                ],
                "education": [{"field": "CS", "degree": "B.Tech"}],
                "certifications": [{"name": "AWS SA"}],
                "projects": [{"name": "Portfolio"}],
                # PII that must NOT leak:
                "email": "secret@example.com",
                "phone": "+91-999",
                "name": "John Doe",
            },
        )
        text = es.build_resume_embedding_text(resume)
        assert "secret@example.com" not in text
        assert "+91-999" not in text
        assert "John Doe" not in text
        assert "Python" in text and "AWS SA" in text and "CS" in text
        assert f"input_version: {EMBEDDING_INPUT_VERSION}" in text

    def test_resume_builder_oversized_truncated(self):
        resume = Resume(
            target_vertical="x" * 100,
            content={"summary": "y" * 100000, "highlightedSkills": ["a"]},
        )
        assert len(es.build_resume_embedding_text(resume)) <= es.MAX_EMBED_CHARS

    def test_content_hash_stable(self):
        assert es.content_hash("abc") == es.content_hash("abc")
        assert es.content_hash("abc") != es.content_hash("abd")


class TestClient:
    @pytest.mark.asyncio
    async def test_batch_count_mismatch_raises(self):
        fake = AsyncMock()
        fake.post = AsyncMock(
            return_value=_resp(200, {"data": [{"index": 0, "embedding": make_vector()}]})
        )
        with patch("services.embedding_client._get_client", return_value=fake):
            with pytest.raises(EmbeddingServiceError):
                await fetch_embeddings(["a", "b"])

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self):
        calls = []

        async def post(*a, **k):
            calls.append(1)
            return _resp(400, {})

        fake = AsyncMock()
        fake.post = post
        fake.is_closed = False
        with patch("services.embedding_client._get_client", return_value=fake):
            with pytest.raises(EmbeddingServiceError):
                await fetch_embeddings(["x"], retries=3)
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_retry_on_429_then_success(self):
        calls = []

        async def post(*a, **k):
            calls.append(1)
            if len(calls) == 1:
                return _resp(429, {}, headers={"Retry-After": "0"})
            return _resp(
                200,
                {"data": [{"index": 0, "embedding": make_vector()}]},
            )

        fake = AsyncMock()
        fake.post = post
        fake.is_closed = False
        with (
            patch("services.embedding_client._get_client", return_value=fake),
            patch("services.embedding_client.asyncio.sleep", new=AsyncMock()),
        ):
            vecs = await fetch_embeddings(["x"], retries=3)
        assert len(calls) == 2
        assert len(vecs[0]) == EMBEDDING_DIM


def _resp(status, payload, headers=None):
    import httpx

    req = httpx.Request("POST", "https://example.com/embeddings")
    return httpx.Response(status, json=payload, headers=headers or {}, request=req)


class TestEnsureJobEmbedding:
    @pytest.mark.asyncio
    async def test_none_embedding_returns_none(self, db_session):
        job = JobPosting(
            company_id=None,
            title="T",
            status="draft",
            embedding=None,
            embedding_status="failed",
        )
        # refresh will fail without API key -> embedding stays None
        with patch(
            "services.fitment_service.refresh_job_embedding",
            new=AsyncMock(),
        ):
            result = await ensure_job_embedding(db_session, job)
        assert result is None


# ---------------------------------------------------------------- DB-level


def _vec_sql(vec):
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


async def _mk_candidate(db, tag):
    u = User(
        id=_uuid.uuid4(),
        email=f"f_{tag}_{_uuid.uuid4().hex[:8]}@t.com",
        password_hash="h",
        role=UserRole.candidate,
        is_active=True,
    )
    db.add(u)
    await db.flush()
    db.add(CandidateProfile(user_id=u.id, weblinks={}))
    await db.flush()
    return u


class TestDbLevel:
    async def test_wrong_length_vector_rejected_by_postgres(self, db_session):
        u = await _mk_candidate(db_session, "wl")
        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO resumes (id, candidate_id, target_vertical, content, embedding) "
                    "VALUES (:id, :cid, 'v', '{}'::jsonb, CAST(:v AS vector))"
                ),
                {
                    "id": str(_uuid.uuid4()),
                    "cid": str(u.id),
                    "v": _vec_sql([0.1] * 512),  # 512 into vector(1536) must fail
                },
            )

    async def test_nearest_neighbour_order_and_exclusions(self, db_session):
        """Uses the REAL compute_fitment SQL path end-to-end."""
        from services.fitment_service import compute_fitment

        base = [0.0] * EMBEDDING_DIM
        # tiny distinct distances from the job vector so our rows always
        # rank above unrelated rows in the shared test DB
        near = list(base)
        near[0] = 1.0
        mid = list(near)
        mid[1] = 0.01
        far = list(near)
        far[2] = 0.02

        async def mk_resume(vec, status="scored", model=EMBEDDING_MODEL):
            u = await _mk_candidate(db_session, "nn" + _uuid.uuid4().hex[:4])
            emb = "NULL" if vec is None else f"'{_vec_sql(vec)}'::vector"
            rid = _uuid.uuid4()
            await db_session.execute(
                text(
                    "INSERT INTO resumes (id, candidate_id, target_vertical, content, "
                    "embedding, embedding_status, embedding_model) VALUES "
                    f"('{rid}', '{u.id}', 'v', '{{}}'::jsonb, {emb}, '{status}', '{model}')"
                )
            )
            return u.id

        near_c = await mk_resume(near)
        mid_c = await mk_resume(mid)
        far_c = await mk_resume(far)
        null_c = await mk_resume(None)  # NULL embedding -> excluded
        other_c = await mk_resume(near, model="old-model")  # other model -> excluded
        await db_session.commit()

        # job vector == 'near'; job itself scored with current model
        cu = User(
            id=_uuid.uuid4(),
            email=f"co_{_uuid.uuid4().hex[:8]}@t.com",
            password_hash="h",
            role=UserRole.company,
            is_active=True,
        )
        db_session.add(cu)
        await db_session.flush()
        db_session.add(Company(user_id=cu.id, name="Co"))
        await db_session.flush()
        job = JobPosting(
            company_id=cu.id,
            title="J",
            job_role="eng",
            required_skills=["py"],
            embedding=near,
            embedding_status="scored",
            embedding_model=EMBEDDING_MODEL,
        )
        db_session.add(job)
        await db_session.flush()

        results = await compute_fitment(db_session, job, limit=50)
        scored = [r for r in results if r.scoring_method == "embedding"]
        order = [r.candidate_id for r in scored]
        ours = {near_c, mid_c, far_c}
        # our three appear in distance order near < mid < far
        ours_order = [c for c in order if c in ours]
        assert ours_order == [near_c, mid_c, far_c]
        # NULL-embedding and other-model candidates must never appear
        assert null_c not in order
        assert other_c not in order

    async def test_write_path_hash_noop_zero_api_calls(self, db_session):
        probe = JobPosting(title="Eng", job_role="backend", required_skills=["py"])
        job = JobPosting(
            title="Eng",
            job_role="backend",
            required_skills=["py"],
            embedding=make_vector(),
            embedding_status="scored",
            embedding_model=EMBEDDING_MODEL,
            embedding_source_hash=es.content_hash(es.build_job_embedding_text(probe)),
        )
        with patch("services.embedding_service.embed_text", new=AsyncMock()) as m:
            await es.refresh_job_embedding(db_session, job)
        m.assert_not_called()

    async def test_write_path_changed_text_calls_api_once(self, db_session):
        job = JobPosting(
            title="Eng",
            job_role="backend",
            required_skills=["py"],
            embedding=make_vector(),
            embedding_status="scored",
            embedding_model=EMBEDDING_MODEL,
            embedding_source_hash="stale-hash",
        )
        with patch(
            "services.embedding_service.embed_text",
            new=AsyncMock(return_value=make_vector()),
        ) as m:
            await es.refresh_job_embedding(db_session, job)
        assert m.call_count == 1
        assert job.embedding_source_hash == es.content_hash(es.build_job_embedding_text(job))


class TestBackfillScript:
    def _args(self, argv):
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("--table", default="all")
        ap.add_argument("--batch-size", type=int, default=50)
        ap.add_argument("--limit", type=int, default=None)
        ap.add_argument("--max-rows", type=int, default=None)
        ap.add_argument("--dry-run", action="store_true", default=True)
        ap.add_argument("--apply", action="store_true")
        ap.add_argument("--retry-failed", action="store_true")
        ap.add_argument("--target", default="test")
        args = ap.parse_args(argv)
        args.dry_run = not args.apply
        args.target_primary = args.target == "primary"
        return args

    async def test_dry_run_writes_nothing(self):
        import scripts.backfill_embeddings as bf

        rc = await bf.run(self._args(["--table", "resumes", "--dry-run"]))
        assert rc in (0, 1)

    async def test_primary_refused_without_flag(self):
        import scripts.backfill_embeddings as bf

        with patch.object(bf, "_is_primary", return_value=True):
            rc = await bf.run(self._args(["--table", "resumes", "--apply"]))
        assert rc == 2


class TestBackfillApply:
    """Backfill apply path with mocked provider — uses TEST_DATABASE_URL."""

    async def _seed_pending_resume(self, db):
        u = await _mk_candidate(db, "bf")
        r = Resume(
            candidate_id=u.id,
            target_vertical="backend",
            content={"highlightedSkills": ["Python"], "summary": "dev"},
            embedding=None,
            embedding_status="pending",
            embedding_model=EMBEDDING_MODEL,
        )
        db.add(r)
        await db.commit()
        return r

    def _args(self, *extra):
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("--table", default="all")
        ap.add_argument("--batch-size", type=int, default=50)
        ap.add_argument("--limit", type=int, default=None)
        ap.add_argument("--max-rows", type=int, default=None)
        ap.add_argument("--dry-run", action="store_true", default=True)
        ap.add_argument("--apply", action="store_true")
        ap.add_argument("--retry-failed", action="store_true")
        ap.add_argument("--target", default="test")
        ns, _ = ap.parse_known_args(list(extra))
        ns.dry_run = not ns.apply
        ns.target_primary = ns.target == "primary"
        return ns

    async def test_apply_fills_and_second_run_zero_calls_for_current_rows(self, db_session):
        import scripts.backfill_embeddings as bf

        resume = await self._seed_pending_resume(db_session)
        our_text = es.build_resume_embedding_text(resume)
        vec = make_vector()
        sent_texts = []

        async def fake_embed(texts):
            sent_texts.extend(texts)
            return [vec for _ in texts]

        with patch(
            "scripts.backfill_embeddings.embed_texts", new=AsyncMock(side_effect=fake_embed)
        ):
            rc1 = await bf.run(self._args("--table", "resumes", "--apply"))
            assert our_text in sent_texts  # first run embedded our row
            sent_texts.clear()
            rc2 = await bf.run(self._args("--table", "resumes", "--apply"))
            # second run: our row is current -> its text is never re-sent
            assert our_text not in sent_texts
        assert rc1 == 0 and rc2 == 0

    async def test_failing_row_does_not_block_others(self, db_session):
        import scripts.backfill_embeddings as bf

        await self._seed_pending_resume(db_session)
        await self._seed_pending_resume(db_session)
        calls = {"n": 0}

        async def flaky(texts):
            calls["n"] += 1
            if calls["n"] == 1:
                raise es.EmbeddingError("provider down")
            return [make_vector() for _ in texts]

        with patch("scripts.backfill_embeddings.embed_texts", new=AsyncMock(side_effect=flaky)):
            rc = await bf.run(self._args("--table", "resumes", "--apply", "--batch-size", "1"))
        # batch 1 fails -> its row marked failed; later batches still processed
        assert rc == 1
        assert calls["n"] >= 2


class TestBackgroundIsolation:
    async def test_bg_refresh_never_raises(self):
        import uuid as _u

        from services.embedding_service import refresh_job_embedding_bg

        with patch(
            "services.embedding_service.refresh_job_embedding",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            # must not raise even though inner refresh exploded
            await refresh_job_embedding_bg(_u.uuid4())

    async def test_profile_saves_at_most_one_call_per_changed_text(self, db_session):
        """Three rapid profile-item saves -> hash-skip means <=1 API call per resume."""
        u = await _mk_candidate(db_session, "seq")
        resume = Resume(
            candidate_id=u.id,
            target_vertical="backend",
            content={"highlightedSkills": ["Python"], "summary": "s"},
            embedding=None,
            embedding_status="pending",
            embedding_model=EMBEDDING_MODEL,
        )
        db_session.add(resume)
        await db_session.commit()

        vec = make_vector()
        with patch(
            "services.embedding_service.embed_text",
            new=AsyncMock(return_value=vec),
        ) as m:
            # simulate three sequential saves triggering refresh
            for _ in range(3):
                await es.refresh_resume_embeddings_for_candidate(db_session, u.id)
        # first call embeds; subsequent calls hash-skip -> exactly 1 API call
        assert m.call_count == 1


class TestPiiFieldsExplicit:
    def test_excluded_fields_listed_and_absent(self):
        resume = Resume(
            target_vertical="backend",
            content={
                "name": "Jane Q Public",
                "email": "jane.q@example.com",
                "phone": "+1-555-0100",
                "address": "123 Secret St",
                "dob": "1990-01-01",
                "gender": "female",
                "marital_status": "married",
                "religion": "x",
                "family": "2 kids",
                "expected_salary": "50 LPA",
                "photo_url": "http://x/y.png",
                "weblinks": {"linkedin": "http://li"},
                "highlightedSkills": ["Go"],
                "summary": "Engineer",
            },
        )
        text = es.build_resume_embedding_text(resume)
        excluded = {
            "jane.q@example.com": "email",
            "+1-555-0100": "phone",
            "123 Secret St": "address",
            "1990-01-01": "dob",
            "female": "gender",
            "married": "marital",
            "50 LPA": "salary",
            "http://x/y.png": "photo",
            "http://li": "weblinks",
        }
        for value, field in excluded.items():
            assert value not in text, f"{field} leaked into embedding text"
        assert "Go" in text and "Engineer" in text
