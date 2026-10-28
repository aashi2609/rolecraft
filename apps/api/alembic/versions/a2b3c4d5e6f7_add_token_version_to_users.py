"""Add token_version to users table for revocation and session invalidation

Revision ID: a2b3c4d5e6f7
Revises: f7a8b9c0d1e2
Create Date: 2026-10-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add token_version column to users with server_default=1
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), server_default='1', nullable=False)
    )


def downgrade() -> None:
    import os
    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing to execute destructive downgrade: dropping token_version column will break "
            "session invalidation and JWT revocation. If this is intentional in a local test, "
            "set ALLOW_DESTRUCTIVE_DOWNGRADE=1. In production, rollback must be performed via "
            "database snapshot restore."
        )
    op.drop_column('users', 'token_version')
