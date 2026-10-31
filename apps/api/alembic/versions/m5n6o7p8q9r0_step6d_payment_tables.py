"""Step 6D: Add payment tables (PricePoint, PaymentTransaction).

Revision ID: m5n6o7p8q9r0
Revises: l3m4n5o6p7q8
Create Date: 2026-10-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "m5n6o7p8q9r0"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create PaymentStatus enum
    payment_status_enum = postgresql.ENUM(
        "pending",
        "completed",
        "failed",
        "cancelled",
        "refunded",
        name="payment_status",
    )
    payment_status_enum.create(op.get_bind())

    # Create BillingPeriod enum
    billing_period_enum = postgresql.ENUM(
        "monthly",
        "quarterly",
        "annual",
        "lifetime",
        name="billing_period",
    )
    billing_period_enum.create(op.get_bind())

    # Create price_points table
    op.create_table(
        "price_points",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "plan_tier",
            sa.Enum(
                "basic",
                "free",
                "premium",
                "elite",
                "starter",
                "growth",
                "scale",
                "resume_builder",
                "job_search",
                "complete",
                "corporate_annual",
                "corporate_lifetime",
                name="plan_tier",
            ),
            nullable=False,
        ),
        sa.Column(
            "billing_period",
            billing_period_enum,
            nullable=False,
        ),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_tier", "billing_period", name="uq_plan_period"),
    )
    op.create_index("ix_price_points_plan_tier", "price_points", ["plan_tier"])
    op.create_index(
        "ix_price_points_billing_period", "price_points", ["billing_period"]
    )

    # Create payment_transactions table
    op.create_table(
        "payment_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "price_point_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("razorpay_order_id", sa.String(255), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(255), nullable=True),
        sa.Column("razorpay_signature", sa.String(255), nullable=True),
        sa.Column(
            "status",
            payment_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("webhook_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "webhook_received_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["price_point_id"], ["price_points.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_order_id", name="uq_razorpay_order_id"),
        sa.UniqueConstraint("razorpay_payment_id", name="uq_razorpay_payment_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_idempotency_key"),
    )
    op.create_index(
        "ix_payment_transactions_user_id",
        "payment_transactions",
        ["user_id"],
    )
    op.create_index(
        "ix_payment_transactions_razorpay_order_id",
        "payment_transactions",
        ["razorpay_order_id"],
    )
    op.create_index(
        "ix_payment_transactions_razorpay_payment_id",
        "payment_transactions",
        ["razorpay_payment_id"],
    )
    op.create_index(
        "ix_payment_transactions_status",
        "payment_transactions",
        ["status"],
    )
    op.create_index(
        "ix_payment_transactions_created_at",
        "payment_transactions",
        ["created_at"],
    )


def downgrade() -> None:
    # Drop payment_transactions table
    op.drop_table("payment_transactions")

    # Drop price_points table
    op.drop_table("price_points")

    # Drop enums
    op.execute("DROP TYPE payment_status CASCADE")
    op.execute("DROP TYPE billing_period CASCADE")
