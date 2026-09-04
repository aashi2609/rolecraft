"""Unit tests for tightened Pydantic schema validation (Tier 3 item 3)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from schemas import (
    ApplicationStatusUpdate,
    ChangePasswordRequest,
    ExperienceIn,
    JobCreate,
    SignupRequest,
)


def test_password_rejects_short_and_weak() -> None:
    with pytest.raises(ValidationError):
        SignupRequest(email="a@b.com", password="short1", role="candidate")
    with pytest.raises(ValidationError):
        SignupRequest(email="a@b.com", password="allletters", role="candidate")
    with pytest.raises(ValidationError):
        SignupRequest(email="a@b.com", password="12345678", role="candidate")


def test_password_accepts_letter_and_digit() -> None:
    body = SignupRequest(email="a@b.com", password="testpass123", role="candidate")
    assert body.password == "testpass123"
    ChangePasswordRequest(current_password="oldpass12", new_password="newpass99")


def test_role_must_be_candidate_or_company() -> None:
    with pytest.raises(ValidationError):
        SignupRequest(email="a@b.com", password="testpass123", role="admin")  # type: ignore[arg-type]
    ok = SignupRequest(email="a@b.com", password="testpass123", role="company")
    assert ok.role == "company"


def test_salary_ge_zero_and_max_gte_min() -> None:
    with pytest.raises(ValidationError):
        JobCreate(title="Eng", min_salary=-1)
    with pytest.raises(ValidationError):
        JobCreate(title="Eng", min_salary=100, max_salary=50)
    ok = JobCreate(
        title="Eng", min_salary=50, max_salary=100, employment_type="Full-time"
    )
    assert ok.max_salary == 100


def test_experience_dates_and_is_current() -> None:
    with pytest.raises(ValidationError):
        ExperienceIn(
            from_date=date(2022, 1, 1), to_date=date(2021, 1, 1), is_current=False
        )
    # is_current=True skips ordering even if to_date < from_date is omitted
    current = ExperienceIn(from_date=date(2022, 1, 1), to_date=None, is_current=True)
    assert current.is_current is True
    ok = ExperienceIn(
        from_date=date(2020, 1, 1), to_date=date(2021, 6, 1), is_current=False
    )
    assert ok.to_date == date(2021, 6, 1)


def test_application_status_matches_db_enum() -> None:
    for s in ("applied", "shortlisted", "rejected", "interview"):
        assert ApplicationStatusUpdate(status=s).status == s  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ApplicationStatusUpdate(status="hired")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ApplicationStatusUpdate(status="pending")  # type: ignore[arg-type]


def test_job_out_accepts_orm_status_enum() -> None:
    """Regression: JobOut Literals must coerce JobStatus/JobType enums (POST /jobs 500)."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from models import JobStatus
    from schemas import JobOut

    class _Row:
        id = uuid4()
        company_id = uuid4()
        title = "Draft Role"
        department = None
        employment_type = None
        experience_range = None
        min_salary = 0
        max_salary = 100
        salary_unit = "Per annum"
        location = None
        country = None
        state = None
        city = None
        job_role = None
        job_level = None
        job_type = None
        required_skills = []
        num_openings = 1
        application_deadline = None
        description = "secret draft"
        responsibilities = None
        requirements = None
        benefits = None
        status = JobStatus.draft
        created_at = datetime.now(timezone.utc)

    out = JobOut.model_validate(_Row())
    assert out.status == "draft"
