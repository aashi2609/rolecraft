"""Add Stage 2 resume AI columns

Revision ID: 0002_resume_ai
Revises: 0001_initial
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_resume_ai"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("ats_breakdown", postgresql.JSONB(), nullable=True))
    op.add_column("resumes", sa.Column("generation_metadata", postgresql.JSONB(), nullable=True))
    op.add_column("resumes", sa.Column("version", sa.Integer(), nullable=True, server_default="1"))
    op.add_column("resumes", sa.Column("pdf_path", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "pdf_path")
    op.drop_column("resumes", "version")
    op.drop_column("resumes", "generation_metadata")
    op.drop_column("resumes", "ats_breakdown")
