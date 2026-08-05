from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str  # candidate | company
    name: Optional[str] = None
    industry: Optional[str] = None
    plan: Optional[str] = "basic"


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: str
    plan: Optional[str] = None


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    role: str
    created_at: datetime


# ── Candidate ─────────────────────────────────────────────────────────────────

class CandidateProfileUpdate(BaseModel):
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


class ProjectOut(ProjectIn, ORMModel):
    id: UUID
    candidate_id: UUID


class SkillsUpdate(BaseModel):
    skills: list[str]


class CandidateProfileOut(ORMModel):
    user_id: UUID
    email: Optional[str] = None
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
    annual_family_income: Optional[str] = None
    skills: list[str] = []
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
    employment_type: Optional[str] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_unit: Optional[str] = "Per annum"
    location: Optional[str] = None
    job_type: Optional[str] = None  # onsite|remote|hybrid
    required_skills: list[str] = []
    num_openings: int = 1
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: str = "draft"


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_unit: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    required_skills: Optional[list[str]] = None
    num_openings: Optional[int] = None
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None


class JobStatusUpdate(BaseModel):
    status: str  # draft|live|closed


class JobOut(ORMModel):
    id: UUID
    company_id: UUID
    company_name: Optional[str] = None
    title: str
    department: Optional[str] = None
    employment_type: Optional[str] = None
    experience_range: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_unit: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    required_skills: Optional[list[str]] = None
    num_openings: int = 1
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    status: str
    created_at: datetime
    matched: int = 0
    shortlisted: int = 0


class FitmentCandidateOut(BaseModel):
    candidate_id: UUID
    name: Optional[str] = None
    title: Optional[str] = None
    score: float
    rationale: Optional[str] = None
    skills: list[str] = []
    location: Optional[str] = None
    experience_years: Optional[int] = None


# ── Applications ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: UUID
    resume_id: Optional[UUID] = None


class ApplicationStatusUpdate(BaseModel):
    status: str


class ApplicationOut(ORMModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    resume_id: Optional[UUID] = None
    status: str
    applied_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None


# ── Messages / Notifications / Subscriptions ──────────────────────────────────

class MessageCreate(BaseModel):
    body: str


class MessageOut(ORMModel):
    id: UUID
    thread_id: UUID
    sender_id: UUID
    sender_role: str
    body: str
    sent_at: datetime


class ThreadOut(BaseModel):
    thread_id: UUID
    last_body: Optional[str] = None
    last_sent_at: Optional[datetime] = None
    participant_label: Optional[str] = None


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
