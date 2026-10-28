"""Sync missing enum values for user_role and plan_tier

Revision ID: b4c5d6e7f8a9
Revises: a2b3c4d5e6f7
Create Date: 2026-10-25 01:25:00.000000

Adds missing enum variants to Postgres ENUM types:
- user_role: 'admin'
- plan_tier: 'resume_builder', 'job_search', 'complete',
             'corporate_annual', 'corporate_lifetime'
"""

from alembic import op

revision = "b4c5d6e7f8a9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL ALTER TYPE ... ADD VALUE cannot run inside a transaction.
    # Use autocommit_block to execute these DDL statements outside the transaction.
    with op.get_context().autocommit_block():
        # Safely add 'admin' to user_role
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin';")

        # Safely add new subscription plans to plan_tier
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'resume_builder';")
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'job_search';")
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'complete';")
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'corporate_annual';")
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'corporate_lifetime';")


def downgrade() -> None:
    # PostgreSQL does not support ALTER TYPE ... DROP VALUE.
    # To remove enum values in Postgres, the type and all referencing tables
    # must be completely recreated. Removing enum values in production would risk
    # corrupting rows with active subscriptions. Hence, this downgrade is a no-op.
    pass
