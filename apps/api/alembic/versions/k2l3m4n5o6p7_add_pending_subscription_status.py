"""Step 6A: Add pending status to subscription_status enum and update signup behavior.

This migration adds 'pending' status to track subscriptions awaiting payment verification.
Signup no longer creates active paid subscriptions automatically.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'k2l3m4n5o6p7'
down_revision = 'j1k2l3m4n5o6'
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
    # Create a new type without 'pending', then swap
    op.execute("""
        -- Create new enum without 'pending'
        CREATE TYPE subscription_status_new AS ENUM ('active', 'cancelled');
        
        -- Update columns to use new enum (convert pending to active)
        ALTER TABLE subscriptions 
            ALTER COLUMN status TYPE subscription_status_new 
            USING CASE 
                WHEN status = 'pending'::text THEN 'active'::subscription_status_new
                ELSE status::subscription_status_new
            END;
        
        -- Drop old enum and rename new one
        DROP TYPE subscription_status;
        ALTER TYPE subscription_status_new RENAME TO subscription_status;
    """)
