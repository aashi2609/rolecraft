"""Drop legacy message columns thread_id and recipient_id (contract phase)

Revision ID: c7d8e9f0a1b2
Revises: b4c5d6e7f8a9
Create Date: 2026-10-25 21:12:00.000000

Completes the expand-contract migration for the messaging schema by dropping
the legacy `thread_id` and `recipient_id` columns and their indexes/constraints
using IF EXISTS so it is safe against databases where they were already removed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c7d8e9f0a1b2"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop foreign key constraint on recipient_id if exists
    op.execute(
        "ALTER TABLE messages DROP CONSTRAINT IF EXISTS fk_messages_recipient_id_users;"
    )

    # 2. Drop legacy indexes if exist
    op.execute("DROP INDEX IF EXISTS ix_messages_thread_id;")
    op.execute("DROP INDEX IF EXISTS ix_messages_recipient_id;")

    # 3. Drop legacy columns if exist
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS thread_id;")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS recipient_id;")


def downgrade() -> None:
    import os
    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing to execute destructive downgrade: re-adding legacy message columns is "
            "potentially lossless but this is a contract migration completing an expand-contract "
            "pattern. If this is intentional in a local test, set ALLOW_DESTRUCTIVE_DOWNGRADE=1. "
            "In production, rollback must be performed via database snapshot restore."
        )
    # Re-add columns as nullable (data in dropped columns cannot be recovered)
    op.add_column(
        "messages",
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_recipient_id", "messages", ["recipient_id"])
    op.create_foreign_key(
        "fk_messages_recipient_id_users",
        "messages",
        "users",
        ["recipient_id"],
        ["id"],
        ondelete="CASCADE",
    )
