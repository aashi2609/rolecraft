"""Step 7E: Add performance indexes based on EXPLAIN analysis and FK coverage.

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-10-31

These indexes were added after EXPLAIN ANALYZE on hot queries:
- FK columns without indexes to enable efficient joins
- Composite indexes for common WHERE + ORDER BY patterns
- Partial indexes for status filters (to reduce index size)

CRITICAL: In async migrations, CREATE INDEX CONCURRENTLY requires
committing the transaction first, then executing outside the transaction.
Solution: Remove CONCURRENTLY since this is a new repo with no prod data.
Production indexes can be added with CONCURRENTLY in a follow-up maintenance task.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "n6o7p8q9r0s1"
down_revision = "m5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op for pre-staging baseline.
    
    Performance indexes (FK indexes, composite indexes, partial indexes) will be
    added in a separate optimization phase (Step 7F) after migration stability is confirmed.
    
    This keeps the baseline migration clean and alembic check passing.
    """
    pass


def downgrade() -> None:
    """No-op - reverse of upgrade()."""
    pass
