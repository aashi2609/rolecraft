"""Add recipient_id to messages for cross-user threads

Revision ID: a1b2c3d4e5f6
Revises: f526df99dd65
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f526df99dd65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_messages_recipient_id", "messages", ["recipient_id"])
    op.create_foreign_key(
        "fk_messages_recipient_id_users",
        "messages",
        "users",
        ["recipient_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_recipient_id_users", "messages", type_="foreignkey")
    op.drop_index("ix_messages_recipient_id", table_name="messages")
    op.drop_column("messages", "recipient_id")
