"""Add profile_updated_at and generated_from_profile_at for stale resume tracking

Revision ID: b3c4d5e6f7a8
Revises: f526df99dd65
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "f526df99dd65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile_updated_at to candidate_profiles
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "profile_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    # Backfill existing rows to now() so current resumes aren't all stale
    op.execute("UPDATE candidate_profiles SET profile_updated_at = NOW() WHERE profile_updated_at IS NULL")

    # Add generated_from_profile_at to resumes
    op.add_column(
        "resumes",
        sa.Column(
            "generated_from_profile_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Backfill: set to same value as profile's profile_updated_at so existing resumes are NOT stale
    op.execute(
        """
        UPDATE resumes r
        SET generated_from_profile_at = cp.profile_updated_at
        FROM candidate_profiles cp
        WHERE r.candidate_id = cp.user_id
        AND r.generated_from_profile_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("resumes", "generated_from_profile_at")
    op.drop_column("candidate_profiles", "profile_updated_at")
