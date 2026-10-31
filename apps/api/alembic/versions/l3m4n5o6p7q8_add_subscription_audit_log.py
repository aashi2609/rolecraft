"""Step 6A: Add subscription audit log table for tracking all changes.

Track who changed what, when, and why for compliance and fraud detection.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'l3m4n5o6p7q8'
down_revision = 'k2l3m4n5o6p7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'subscription_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Admin who made the change (NULL if system)'),
        sa.Column('action', sa.String(64), nullable=False, comment='create, update_plan, update_status, cancel, delete'),
        sa.Column('old_plan_tier', sa.String(64), nullable=True),
        sa.Column('new_plan_tier', sa.String(64), nullable=True),
        sa.Column('old_status', sa.String(64), nullable=True),
        sa.Column('new_status', sa.String(64), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True, comment='Payment verified, Admin override, etc.'),
        sa.Column('payment_transaction_id', sa.String(255), nullable=True, comment='Transaction ID if payment-related'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_subscription_audit_log_subscription_id', 'subscription_audit_log', ['subscription_id'])
    op.create_index('ix_subscription_audit_log_user_id', 'subscription_audit_log', ['user_id'])
    op.create_index('ix_subscription_audit_log_admin_id', 'subscription_audit_log', ['admin_id'])
    op.create_index('ix_subscription_audit_log_created_at', 'subscription_audit_log', ['created_at'])


def downgrade() -> None:
    op.drop_table('subscription_audit_log')
