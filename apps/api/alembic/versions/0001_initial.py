"""Initial schema + pgvector extension

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    user_role = postgresql.ENUM("candidate", "company", name="user_role", create_type=False)
    plan_tier = postgresql.ENUM(
        "free", "basic", "premium", "elite", "starter", "growth", "scale", name="plan_tier", create_type=False
    )
    subscription_status = postgresql.ENUM("active", "cancelled", name="subscription_status", create_type=False)
    job_type = postgresql.ENUM("onsite", "remote", "hybrid", name="job_type", create_type=False)
    job_status = postgresql.ENUM("draft", "live", "closed", name="job_status", create_type=False)
    application_status = postgresql.ENUM(
        "applied", "shortlisted", "rejected", "interview", name="application_status", create_type=False
    )

    op.execute("CREATE TYPE user_role AS ENUM ('candidate', 'company')")
    op.execute(
        "CREATE TYPE plan_tier AS ENUM ('free', 'basic', 'premium', 'elite', 'starter', 'growth', 'scale')"
    )
    op.execute("CREATE TYPE subscription_status AS ENUM ('active', 'cancelled')")
    op.execute("CREATE TYPE job_type AS ENUM ('onsite', 'remote', 'hybrid')")
    op.execute("CREATE TYPE job_status AS ENUM ('draft', 'live', 'closed')")
    op.execute(
        "CREATE TYPE application_status AS ENUM ('applied', 'shortlisted', 'rejected', 'interview')"
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("plan_tier", plan_tier, nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("photo_url", sa.String(1024)),
        sa.Column("career_level", sa.String(64)),
        sa.Column("dob", sa.Date()),
        sa.Column("gender", sa.String(32)),
        sa.Column("marital_status", sa.String(32)),
        sa.Column("present_address", sa.Text()),
        sa.Column("permanent_address", sa.Text()),
        sa.Column("preferred_locations", postgresql.ARRAY(sa.String())),
        sa.Column("preferred_sectors", postgresql.ARRAY(sa.String())),
        sa.Column("strengths", postgresql.ARRAY(sa.String())),
        sa.Column("weaknesses", postgresql.ARRAY(sa.String())),
        sa.Column("weblinks", postgresql.JSONB()),
        sa.Column("annual_family_income", sa.String(64)),
    )

    op.create_table(
        "companies",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("logo_url", sa.String(1024)),
        sa.Column("about", sa.Text()),
        sa.Column("size", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("hq_location", sa.String(255)),
        sa.Column("industry", sa.String(128)),
    )

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)

    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("qualification_level", sa.String(64)),
        sa.Column("degree", sa.String(128)),
        sa.Column("institute", sa.String(255)),
        sa.Column("field_of_study", sa.String(128)),
        sa.Column("passing_year", sa.Integer()),
        sa.Column("cgpa", sa.String(32)),
        sa.Column("marksheet_url", sa.String(1024)),
        sa.Column("certificate_url", sa.String(1024)),
    )
    op.create_index("ix_education_candidate_id", "education", ["candidate_id"])

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuing_org", sa.String(255)),
        sa.Column("completion_date", sa.Date()),
        sa.Column("duration", sa.String(64)),
        sa.Column("credential_id", sa.String(128)),
        sa.Column("description", sa.Text()),
        sa.Column("file_url", sa.String(1024)),
    )
    op.create_index("ix_certifications_candidate_id", "certifications", ["candidate_id"])

    op.create_table(
        "experience",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("company_name", sa.String(255)),
        sa.Column("role", sa.String(128)),
        sa.Column("designation", sa.String(128)),
        sa.Column("employment_type", sa.String(64)),
        sa.Column("current_salary", sa.String(64)),
        sa.Column("expected_salary", sa.String(64)),
        sa.Column("from_date", sa.Date()),
        sa.Column("to_date", sa.Date()),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("responsibilities", sa.Text()),
        sa.Column("gap_from", sa.Date()),
        sa.Column("gap_to", sa.Date()),
        sa.Column("gap_reason", sa.Text()),
    )
    op.create_index("ix_experience_candidate_id", "experience", ["candidate_id"])

    op.create_table(
        "candidate_skills",
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_candidate_skills_skill_id", "candidate_skills", ["skill_id"])

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("org", sa.String(255)),
        sa.Column("project_name", sa.String(255)),
        sa.Column("team_size", sa.Integer()),
        sa.Column("tools_used", sa.String(512)),
        sa.Column("from_date", sa.Date()),
        sa.Column("to_date", sa.Date()),
        sa.Column("responsibilities", sa.Text()),
        sa.Column("achievements", sa.Text()),
    )
    op.create_index("ix_projects_candidate_id", "projects", ["candidate_id"])

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("target_vertical", sa.String(128), nullable=False),
        sa.Column("content", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("ats_score", sa.Integer()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("gcs_path", sa.String(1024)),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])

    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.user_id", ondelete="CASCADE")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(128)),
        sa.Column("employment_type", sa.String(64)),
        sa.Column("experience_range", sa.String(64)),
        sa.Column("min_salary", sa.Integer()),
        sa.Column("max_salary", sa.Integer()),
        sa.Column("salary_unit", sa.String(32)),
        sa.Column("location", sa.String(255)),
        sa.Column("job_type", job_type),
        sa.Column("required_skills", postgresql.ARRAY(sa.String())),
        sa.Column("num_openings", sa.Integer(), server_default="1"),
        sa.Column("application_deadline", sa.Date()),
        sa.Column("description", sa.Text()),
        sa.Column("responsibilities", sa.Text()),
        sa.Column("requirements", sa.Text()),
        sa.Column("benefits", sa.Text()),
        sa.Column("status", job_status, server_default="draft"),
        sa.Column("embedding", Vector(1536)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_job_postings_company_id", "job_postings", ["company_id"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE")),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("status", application_status, server_default="applied"),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_application"),
    )
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_resume_id", "applications", ["resume_id"])

    op.create_table(
        "saved_jobs",
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_saved_jobs_job_id", "saved_jobs", ["job_id"])

    op.create_table(
        "fitment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_fitment"),
    )
    op.create_index("ix_fitment_results_job_id", "fitment_results", ["job_id"])
    op.create_index("ix_fitment_results_candidate_id", "fitment_results", ["candidate_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("sender_role", user_role),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_id", sa.String(64)),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    for table in [
        "notifications",
        "messages",
        "fitment_results",
        "saved_jobs",
        "applications",
        "job_postings",
        "resumes",
        "projects",
        "candidate_skills",
        "experience",
        "certifications",
        "education",
        "skills",
        "companies",
        "candidate_profiles",
        "subscriptions",
        "users",
    ]:
        op.drop_table(table)
    for t in [
        "application_status",
        "job_status",
        "job_type",
        "subscription_status",
        "plan_tier",
        "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {t}")
