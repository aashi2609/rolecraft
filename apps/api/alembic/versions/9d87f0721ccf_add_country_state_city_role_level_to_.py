"""add_country_state_city_role_level_to_jobs_and_hidden_jobs_table

Revision ID: 9d87f0721ccf
Revises: 0002_resume_ai
Create Date: 2026-08-20 00:38:30.346166
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9d87f0721ccf"
down_revision: Union[str, None] = "0002_resume_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hidden_jobs table
    op.create_table(
        "hidden_jobs",
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column(
            "hidden_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidate_id", "job_id"),
    )
    op.create_index(
        op.f("ix_hidden_jobs_job_id"), "hidden_jobs", ["job_id"], unique=False
    )

    # Add new columns to job_postings
    op.add_column(
        "job_postings", sa.Column("country", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "job_postings", sa.Column("state", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "job_postings", sa.Column("city", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "job_postings", sa.Column("job_role", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "job_postings", sa.Column("job_level", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("job_postings", "job_level")
    op.drop_column("job_postings", "job_role")
    op.drop_column("job_postings", "city")
    op.drop_column("job_postings", "state")
    op.drop_column("job_postings", "country")
    op.drop_index(op.f("ix_hidden_jobs_job_id"), table_name="hidden_jobs")
    op.drop_table("hidden_jobs")
