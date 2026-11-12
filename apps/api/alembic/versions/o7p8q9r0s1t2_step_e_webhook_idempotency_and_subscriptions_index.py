"""Step E: Add webhook idempotency tracking and unique index for active subscriptions.

Additions:
1. webhook_events table: Tracks Razorpay webhook event IDs for idempotency
2. Unique index on (user_id) WHERE status='active': Ensures max one active subscription per user

Revision ID: o7p8q9r0s1t2
Revises: n6o7p8q9r0s1
Create Date: 2026-11-07

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "o7p8q9r0s1t2"
down_revision = "n6o7p8q9r0s1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_events table for idempotency tracking
    op.create_table(
        "webhook_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="razorpay"),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "payment_transaction_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("event_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["payment_transaction_id"],
            ["payment_transactions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_event_id", name="uq_webhook_event_provider_event_id"
        ),
    )
    op.create_index(
        "ix_webhook_events_provider_event_id",
        "webhook_events",
        ["provider_event_id"],
    )
    op.create_index(
        "ix_webhook_events_event_type",
        "webhook_events",
        ["event_type"],
    )
    op.create_index(
        "ix_webhook_events_processed",
        "webhook_events",
        ["processed"],
    )
    op.create_index(
        "ix_webhook_events_received_at",
        "webhook_events",
        ["received_at"],
    )

    # Add partial unique index on subscriptions for active subscriptions per user
    # This ensures only one active subscription per user at the DB level
    op.execute(
        """
        CREATE UNIQUE INDEX idx_user_active_subscription 
        ON subscriptions(user_id) 
        WHERE status = 'active'
        """
    )


def downgrade() -> None:
    # Drop the partial unique index on subscriptions
    op.execute("DROP INDEX IF EXISTS idx_user_active_subscription")

    # Drop webhook_events table
    op.drop_table("webhook_events")

