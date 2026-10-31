"""Add scoring_method field to fitment_results for tracking embedding vs heuristic

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-10-31

Step 5A: Track whether fitment scores are embedding-based (real) or heuristic (fallback).
- Add scoring_method field: "embedding" | "heuristic"
- Default to "embedding" for backward compatibility
- Future updates will set "heuristic" when skill-overlap fallback is used
"""

from alembic import op
import sqlalchemy as sa

revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'fitment_results',
        sa.Column(
            'scoring_method',
            sa.String(20),
            nullable=False,
            server_default='embedding'
        )
    )


def downgrade() -> None:
    import os
    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing to execute destructive downgrade: dropping scoring_method column from fitment_results table. "
            "If this is intentional in a local test, set ALLOW_DESTRUCTIVE_DOWNGRADE=1. "
            "In production, rollback must be performed via database snapshot restore."
        )
    
    op.drop_column('fitment_results', 'scoring_method')
