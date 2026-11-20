"""Step 6A: Add pending status to subscription_status enum and update signup behavior.

This migration adds 'pending' status to track subscriptions awaiting payment verification.
Signup no longer creates active paid subscriptions automatically.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'pending' value to subscription_status enum
    # Strategy: Use raw SQL to alter the enum type
    op.execute("""
        ALTER TYPE subscription_status ADD VALUE 'pending' BEFORE 'active';
    """)


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values, so we use a workaround:
    # Create a new type without 'pending', then swap.
    # NOTE: asyncpg rejects multi-statement strings in one execute — split them.
    op.execute("CREATE TYPE subscription_status_new AS ENUM ('active', 'cancelled')")
    op.execute("""
        ALTER TABLE subscriptions
            ALTER COLUMN status TYPE subscription_status_new
            USING CASE
                WHEN status::text = 'pending' THEN 'active'::subscription_status_new
                ELSE status::text::subscription_status_new
            END
    """)
    op.execute("DROP TYPE subscription_status")
    op.execute("ALTER TYPE subscription_status_new RENAME TO subscription_status")
