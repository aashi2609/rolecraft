"""Step F: embedding dimension 512 -> 1536 (native text-embedding-3-small) + source hash.

- Adds embedding_source_hash (text, nullable) to resumes and job_postings.
- Existing vectors are mock/old-dimension and cannot be cast: NULL them,
  set embedding_status='pending', then ALTER COLUMN TYPE vector(1536).
- No ANN index exists or is created (exact scan is correct at current volume;
  revisit with EXPLAIN if resumes grow into the tens of thousands).

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
"""

import os

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "p8q9r0s1t2u3"
down_revision = "o7p8q9r0s1t2"
branch_labels = None
depends_on = None

# Hardcoded: migrations cannot import application code.
# tests/test_embedding_config_consistency.py asserts this equals
# core.embedding_config.EMBEDDING_DIM.
TARGET_DIM = 1536
TABLES = ("resumes", "job_postings")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("embedding_source_hash", sa.String(length=64), nullable=True),
        )
        # Stored vectors are old-dimension/mock and cannot be cast to vector(1536).
        op.execute(f"UPDATE {table} SET embedding = NULL")
        op.execute(
            f"UPDATE {table} SET embedding_status = 'pending'"
        )
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN embedding "
            f"TYPE vector({TARGET_DIM}) USING NULL::vector({TARGET_DIM})"
        )


def downgrade() -> None:

    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing destructive downgrade: this drops embedding_source_hash and "
            "truncates embeddings back to vector(512). Set "
            "ALLOW_DESTRUCTIVE_DOWNGRADE=1 for local test rollbacks only; in "
            "production restore from snapshot instead."
        )

    for table in TABLES:
        op.execute(f"UPDATE {table} SET embedding = NULL")
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN embedding "
            "TYPE vector(512) USING NULL::vector(512)"
        )
        op.drop_column(table, "embedding_source_hash")
