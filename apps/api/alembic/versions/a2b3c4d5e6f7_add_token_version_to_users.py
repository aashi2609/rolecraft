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
    op.drop_column('users', 'token_version')
