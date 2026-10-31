"""Add ats_status field to resumes for explicit error handling

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-10-31

Step 5A: Replace fake fallback scores with explicit status tracking.
- Make ats_score nullable (already nullable)
- Add ats_status enum field: scored | unavailable | error
- Default existing resumes to 'scored' if ats_score IS NOT NULL, else 'unavailable'
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'h9i0j1k2l3m4'
down_revision = '43b4f33a0dcf'  # After merge migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type with explicit name
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ats_score_status AS ENUM ('scored', 'unavailable', 'error');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add the column with default 'unavailable'
    op.add_column(
        'resumes',
        sa.Column(
            'ats_status',
            sa.Enum('scored', 'unavailable', 'error', name='ats_score_status'),
            nullable=False,
            server_default='unavailable'
        )
    )
    
    # Migrate existing data: if ats_score exists, mark as 'scored', else 'unavailable'
    op.execute("""
        UPDATE resumes 
        SET ats_status = CASE 
            WHEN ats_score IS NOT NULL THEN 'scored'::ats_score_status
            ELSE 'unavailable'::ats_score_status
        END
    """)


def downgrade() -> None:
    import os
    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing to execute destructive downgrade: dropping ats_status column from resumes table. "
            "If this is intentional in a local test, set ALLOW_DESTRUCTIVE_DOWNGRADE=1. "
            "In production, rollback must be performed via database snapshot restore."
        )
    
    op.drop_column('resumes', 'ats_status')
    
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS ats_score_status CASCADE')
