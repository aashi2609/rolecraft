from datetime import date, datetime
from typing import Any, Optional, Literal
from uuid import UUID
import enum
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _coerce_enum_value(v: Any) -> Any:
    """Accept SQLAlchemy/Python Enum instances when validating Literal fields."""
    if isinstance(v, enum.Enum):
        return v.value
    return v


def _validate_password_strength(password: str) -> str:
    """Shared password rule: min 8 chars, at least one letter and one number."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    return password


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["candidate", "company"]
    name: Optional[str] = None
    industry: Optional[str] = None
    plan: Optional[str] = "basic"

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_strength(v)


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_strength(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: Literal["candidate", "company", "admin"]
    plan: Optional[str] = None


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    role: Literal["candidate", "company", "admin"]
    created_at: datetime


# ── Candidate ─────────────────────────────────────────────────────────────────

class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    career_level: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    preferred_locations: Optional[list[str]] = None
    preferred_sectors: Optional[list[str]] = None
    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    weblinks: Optional[dict[str, Any]] = None
    notification_prefs: Optional[dict[str, bool]] = None
    annual_family_income: Optional[str] = None


class EducationIn(BaseModel):
    qualification_level: Optional[str] = None
    degree: Optional[str] = None
    institute: Optional[str] = None
    field_of_study: Optional[str] = None
    passing_year: Optional[int] = None
    cgpa: Optional[str] = None
    marksheet_url: Optional[str] = None
    certificate_url: Optional[str] = None


class EducationOut(EducationIn, ORMModel):
    id: UUID
    candidate_id: UUID


class CertificationIn(BaseModel):
    name: str
    issuing_org: Optional[str] = None
    completion_date: Optional[date] = None
    duration: Optional[str] = None
    credential_id: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None


class CertificationOut(CertificationIn, ORMModel):
    id: UUID
    candidate_id: UUID


class ExperienceIn(BaseModel):
    company_name: Optional[str] = None
    role: Optional[str] = None
    designation: Optional[str] = None
    # Free-form (onboarding accepts values like "Full-time, Contract"); jobs use strict Literals
    employment_type: Optional[str] = None
    current_salary: Optional[str] = None
    expected_salary: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    is_current: bool = False
    responsibilities: Optional[str] = None
    gap_from: Optional[date] = None
    gap_to: Optional[date] = None
    gap_reason: Optional[str] = None

    @field_validator("to_date")
    @classmethod
    def validate_to_date(cls, v: Optional[date], info) -> Optional[date]:
        # Current roles may omit to_date; skip ordering check when is_current=True
        if info.data.get("is_current"):
            return v
        if v is not None and info.data.get("from_date") is not None:
            if v < info.data["from_date"]:
                raise ValueError("to_date must be >= from_date")
        return v


class ExperienceOut(ExperienceIn, ORMModel):
    id: UUID
    candidate_id: UUID


class ProjectIn(BaseModel):
    org: Optional[str] = None
    project_name: Optional[str] = None
    team_size: Optional[int] = None
    tools_used: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    responsibilities: Optional[str] = None
    achievements: Optional[str] = None

    @field_validator("to_date")
    @classmethod
    def validate_to_date(cls, v: Optional[date], info) -> Optional[date]:
        if v is not None and info.data.get("from_date") is not None:
            if v < info.data["from_date"]:
                raise ValueError("to_date must be >= from_date")
        return v


class ProjectOut(ProjectIn, ORMModel):
    id: UUID
    candidate_id: UUID


class SkillsUpdate(BaseModel):
    skills: list[str]


class CandidateProfileOut(ORMModel):
    user_id: UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    career_level: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    preferred_locations: Optional[list[str]] = None
    preferred_sectors: Optional[list[str]] = None
    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    weblinks: Optional[dict[str, Any]] = None
    notification_prefs: Optional[dict[str, bool]] = None
    annual_family_income: Optional[str] = None
    skills: list[str] = []
    education: list[EducationOut] = []
    certifications: list[CertificationOut] = []
    experience: list[ExperienceOut] = []
    projects: list[ProjectOut] = []


class CandidatePublicProfileOut(ORMModel):
    """Hiring-safe candidate view — excludes PII."""

    user_id: UUID
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    career_level: Optional[str] = None
    skills: list[str] = []
    strengths: list[str] = []
    weblinks: dict[str, Any] = {}
    education: list[EducationOut] = []
    certifications: list[CertificationOut] = []
    experience: list[ExperienceOut] = []
    projects: list[ProjectOut] = []


# ── Resumes ───────────────────────────────────────────────────────────────────

class ResumeGenerateRequest(BaseModel):
    target_verticals: list[str]


class ResumeOut(ORMModel):
    id: UUID
    candidate_id: UUID
    target_vertical: str
    content: dict[str, Any]
    ats_score: Optional[int] = None
    ats_breakdown: Optional[dict[str, Any]] = None
    version: int = 1
    gcs_path: Optional[str] = None
    pdf_path: Optional[str] = None
    is_default: bool = False
    created_at: datetime


# ── Company ───────────────────────────────────────────────────────────────────

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    about: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    hq_location: Optional[str] = None
    industry: Optional[str] = None


class CompanyOut(ORMModel):
    user_id: UUID
    name: str
    logo_url: Optional[str] = None
    about: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    hq_location: Optional[str] = None
    industry: Optional[str] = None


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    # Match frontend EMPLOYMENT_TYPES (lib/constants.ts)
    employment_type: Optional[Literal["Full-time", "Part-time", "Contract", "Internship"]] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = Field(default=None, ge=0)
    max_salary: Optional[int] = Field(default=None, ge=0)
    salary_unit: Optional[str] = "Per annum"
    location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    job_role: Optional[str] = None
    job_level: Optional[str] = None
    job_type: Optional[Literal["onsite", "remote", "hybrid"]] = None
    required_skills: list[str] = []
    num_openings: int = 1
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: Literal["draft", "live", "closed"] = "draft"

    @field_validator("max_salary")
    @classmethod
    def validate_max_salary(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and info.data.get("min_salary") is not None:
            if v < info.data["min_salary"]:
                raise ValueError("max_salary must be >= min_salary")
        return v


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[Literal["Full-time", "Part-time", "Contract", "Internship"]] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = Field(default=None, ge=0)
    max_salary: Optional[int] = Field(default=None, ge=0)
    salary_unit: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    job_role: Optional[str] = None
    job_level: Optional[str] = None
    job_type: Optional[Literal["onsite", "remote", "hybrid"]] = None
    required_skills: Optional[list[str]] = None
    num_openings: Optional[int] = None
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None

    @field_validator("max_salary")
    @classmethod
    def validate_max_salary(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None and info.data.get("min_salary") is not None:
            if v < info.data["min_salary"]:
                raise ValueError("max_salary must be >= min_salary")
        return v


class JobStatusUpdate(BaseModel):
    status: Literal["draft", "live", "closed"]


class JobOut(ORMModel):
    id: UUID
    company_id: UUID
    company_name: Optional[str] = None
    title: str
    department: Optional[str] = None
    # Optional[str] so legacy admin values (e.g. full_time) still serialize
    employment_type: Optional[str] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_unit: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    job_role: Optional[str] = None
    job_level: Optional[str] = None
    job_type: Optional[Literal["onsite", "remote", "hybrid"]] = None
    required_skills: Optional[list[str]] = None
    num_openings: int = 1
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: Literal["draft", "live", "closed"]
    created_at: datetime
    # Computed in enrich_job (job_search_service), not ORM columns:
    # matched = COUNT(applications) for this job; shortlisted = COUNT where status=shortlisted.
    # Default 0 only until enrichment runs (e.g. create_job error fallback).
    matched: int = 0
    shortlisted: int = 0

    @field_validator("status", "job_type", mode="before")
    @classmethod
    def coerce_job_enums(cls, v: Any) -> Any:
        return _coerce_enum_value(v)


class FitmentCandidateOut(BaseModel):
    candidate_id: UUID
    name: Optional[str] = None
    title: Optional[str] = None
    score: float
    rationale: Optional[str] = None
    rationale_source: Optional[Literal["llm", "template"]] = None
    skills: list[str] = []
    location: Optional[str] = None
    experience_years: Optional[int] = None


# ── Applications ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: UUID
    resume_id: Optional[UUID] = None


class ApplicationStatusUpdate(BaseModel):
    status: Literal["applied", "shortlisted", "rejected", "interview"]


class ApplicationOut(ORMModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    resume_id: Optional[UUID] = None
    status: Literal["applied", "shortlisted", "rejected", "interview"]
    applied_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    candidate_name: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def coerce_application_status(cls, v: Any) -> Any:
        return _coerce_enum_value(v)


# ── Messages / Notifications / Subscriptions ──────────────────────────────────

class MessageCreate(BaseModel):
    body: str
    recipient_id: Optional[UUID] = None


class MessageOut(ORMModel):
    id: UUID
    thread_id: UUID
    sender_id: UUID
    recipient_id: Optional[UUID] = None
    sender_role: str
    body: str
    sent_at: datetime


class ThreadOut(BaseModel):
    thread_id: UUID
    last_body: Optional[str] = None
    last_sent_at: Optional[datetime] = None
    participant_label: Optional[str] = None
    other_user_id: Optional[UUID] = None


class NotificationOut(ORMModel):
    id: UUID
    type: str
    body: str
    related_id: Optional[str] = None
    is_read: bool
    created_at: datetime


class SubscriptionOut(ORMModel):
    id: UUID
    role: str
    plan_tier: str
    status: str
    started_at: datetime
    renews_at: Optional[datetime] = None


class SubscriptionCreate(BaseModel):
    plan_tier: str


class UploadOut(BaseModel):
    url: str
    path: str


# ── Candidate Search ─────────────────────────────────────────────────────────────

class CandidateSearchOut(ORMModel):
    id: UUID
    name: Optional[str] = None
    title: Optional[str] = None
    experience_years: Optional[int] = None
    location: Optional[str] = None
    skills: list[str] = []
    match_percent: float = 0.0
    education: Optional[str] = None
    expected_salary_lpa: Optional[int] = None
    notice_period_days: Optional[int] = None
    photo_url: Optional[str] = None
    rationale: Optional[str] = None
    rationale_source: Optional[Literal["llm", "template"]] = None


# ── Analytics ────────────────────────────────────────────────────────────────────

class TrendPointOut(BaseModel):
    date: str
    count: int


class CandidateAnalyticsOut(BaseModel):
    period_days: int
    total_applications: int
    saved_jobs: int
    average_fitment_score: float
    status_distribution: dict[str, int]
    application_trend: list[TrendPointOut]


class CompanyAnalyticsOut(BaseModel):
    period_days: int
    total_jobs: int
    total_applications: int
    average_fitment_score: float
    status_distribution: dict[str, int]
    response_rate: float
    application_trend: list[TrendPointOut]
