"""Unit tests for resume API-key backup paths (deterministic force + mark-current)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from routers import resumes as resumes_router
from services import resume_service


@pytest.mark.asyncio
async def test_force_deterministic_skips_ai():
    profile = MagicMock()
    profile.experience = []
    profile.education = []
    profile.projects = []
    profile.certifications = []

    with (
        patch.object(resume_service.settings, "force_deterministic_resumes", True),
        patch.object(
            resume_service,
            "_generate_deterministic",
            new_callable=AsyncMock,
            return_value={"content": {"summary": "stub"}, "ats_score": 80, "embedding": []},
        ) as det,
        patch.object(
            resume_service,
            "generate_with_autofix",
            new_callable=AsyncMock,
        ) as ai,
    ):
        result = await resume_service.generate_resume_for_vertical(
            profile, "Software", ["Python"]
        )

    assert result["ats_score"] == 80
    det.assert_awaited_once()
    ai.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_current_sets_generated_from_profile_at():
    resume_id = uuid4()
    user = MagicMock()
    user.id = uuid4()

    row = MagicMock()
    row.candidate_id = user.id
    row.generated_from_profile_at = None

    profile_updated_at = MagicMock()

    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch.object(
            resumes_router,
            "_get_profile_updated_at",
            new_callable=AsyncMock,
            return_value=profile_updated_at,
        ),
        patch.object(
            resumes_router,
            "_resume_to_out",
            return_value=MagicMock(is_stale=False, id=resume_id),
        ) as to_out,
    ):
        out = await resumes_router.mark_current(resume_id, user, db)

    assert row.generated_from_profile_at is profile_updated_at
    db.flush.assert_awaited_once()
    to_out.assert_called_once_with(row, profile_updated_at)
    assert out.is_stale is False


def test_mark_current_route_registered():
    paths = {getattr(r, "path", None) for r in resumes_router.router.routes}
    assert "/resumes/{resume_id}/mark-current" in paths
