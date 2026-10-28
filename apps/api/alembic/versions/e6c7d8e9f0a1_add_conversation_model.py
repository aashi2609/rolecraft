"""Add conversation model (data-preserving rewrite)

Revision ID: e6c7d8e9f0a1
Revises: d5b69ec5aecb
Create Date: 2026-09-29 00:00:00.000000

Restructures messages from thread_id + recipient_id to a first-class
conversations table. Every existing message is either mapped to an
inferred conversation or moved to messages_quarantine. No rows are
deleted. Old columns (thread_id, recipient_id) are kept for rollback
safety; a later contract migration can drop them.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e6c7d8e9f0a1"
down_revision = "d5b69ec5aecb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Snapshot original message count for row-count assertion ──────
    original_count = conn.execute(
        sa.text("SELECT count(*) FROM messages")
    ).scalar()

    # ── 1. Create conversations table ────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.user_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["job_postings.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "candidate_id",
            name="uq_conversation_participants",
        ),
    )
    op.create_index(
        op.f("ix_conversations_candidate_id"),
        "conversations",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_company_id"),
        "conversations",
        ["company_id"],
        unique=False,
    )

    # ── 2. Create quarantine table (preserves all original columns) ───
    op.create_table(
        "messages_quarantine",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "sender_role",
            postgresql.ENUM(
                "candidate", "company", "admin",
                name="user_role",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("quarantine_reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 3. Add new columns to messages as NULLABLE first ─────────────
    op.add_column(
        "messages",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,  # nullable for now; enforced after backfill
        ),
    )
    op.add_column(
        "messages",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 4. Backfill conversations using multi-level participant inference
    #
    # Inference tiers:
    # 1. Direct (sender_role + recipient_id on the message)
    # 2. Thread peers (another message in the same thread_id has the other role)
    # 3. Application linkage (thread_id matches applications.id -> job -> company + candidate)
    # 4. Job linkage (thread_id matches job_postings.id -> company)
    #
    # Then validate that both participants exist in companies and candidate_profiles.
    conn.execute(sa.text("""
        CREATE TEMPORARY TABLE _msg_inference AS
        WITH direct_pairs AS (
            SELECT
                m.id AS message_id,
                CASE 
                    WHEN m.sender_role = 'company'   THEN m.sender_id
                    WHEN m.sender_role = 'candidate'  THEN m.recipient_id
                END AS company_id,
                CASE 
                    WHEN m.sender_role = 'candidate'  THEN m.sender_id
                    WHEN m.sender_role = 'company'    THEN m.recipient_id
                END AS candidate_id,
                CAST(NULL AS UUID) AS job_id,
                m.sent_at
            FROM messages m
            WHERE m.sender_role IN ('company', 'candidate')
              AND m.recipient_id IS NOT NULL
        ),
        thread_peers AS (
            SELECT
                m.thread_id,
                MAX(CASE WHEN m.sender_role = 'company'   THEN m.sender_id::text END)::uuid AS company_id,
                MAX(CASE WHEN m.sender_role = 'candidate' THEN m.sender_id::text END)::uuid AS candidate_id
            FROM messages m
            WHERE m.thread_id IS NOT NULL
            GROUP BY m.thread_id
            HAVING MAX(CASE WHEN m.sender_role = 'company'   THEN m.sender_id::text END) IS NOT NULL
               AND MAX(CASE WHEN m.sender_role = 'candidate' THEN m.sender_id::text END) IS NOT NULL
        ),
        app_linkage AS (
            SELECT
                a.id AS thread_id,
                jp.company_id AS company_id,
                a.candidate_id AS candidate_id,
                a.job_id AS job_id
            FROM applications a
            JOIN job_postings jp ON jp.id = a.job_id
        ),
        job_linkage AS (
            SELECT
                jp.id AS thread_id,
                jp.company_id AS company_id,
                jp.id AS job_id
            FROM job_postings jp
        )
        SELECT
            m.id AS message_id,
            m.sent_at,
            COALESCE(
                dp.company_id,
                tp.company_id,
                al.company_id,
                jl.company_id
            ) AS company_id,
            COALESCE(
                dp.candidate_id,
                tp.candidate_id,
                al.candidate_id,
                CASE WHEN m.sender_role = 'candidate' THEN m.sender_id ELSE m.recipient_id END
            ) AS candidate_id,
            COALESCE(al.job_id, jl.job_id) AS job_id
        FROM messages m
        LEFT JOIN direct_pairs dp ON dp.message_id = m.id
        LEFT JOIN thread_peers tp ON tp.thread_id = m.thread_id
        LEFT JOIN app_linkage  al ON al.thread_id = m.thread_id
        LEFT JOIN job_linkage  jl ON jl.thread_id = m.thread_id;
    """))

    # Step 4a: Insert distinct valid conversations
    conn.execute(sa.text("""
        INSERT INTO conversations (id, company_id, candidate_id, job_id, created_at, last_message_at)
        SELECT
            gen_random_uuid(),
            inf.company_id,
            inf.candidate_id,
            MAX(inf.job_id::text)::uuid,
            MIN(inf.sent_at),
            MAX(inf.sent_at)
        FROM _msg_inference inf
        JOIN companies c ON c.user_id = inf.company_id
        JOIN candidate_profiles cp ON cp.user_id = inf.candidate_id
        WHERE inf.company_id IS NOT NULL AND inf.candidate_id IS NOT NULL
        GROUP BY inf.company_id, inf.candidate_id
        ON CONFLICT (company_id, candidate_id) DO UPDATE
            SET job_id = COALESCE(conversations.job_id, EXCLUDED.job_id),
                last_message_at = GREATEST(conversations.last_message_at, EXCLUDED.last_message_at)
    """))

    # Step 4b: Backfill conversation_id into messages
    conn.execute(sa.text("""
        UPDATE messages m
        SET conversation_id = conv.id
        FROM _msg_inference inf
        JOIN conversations conv 
          ON conv.company_id = inf.company_id 
         AND conv.candidate_id = inf.candidate_id
        WHERE m.id = inf.message_id
          AND m.conversation_id IS NULL
    """))

    conn.execute(sa.text("DROP TABLE _msg_inference"))

    # ── 5. Quarantine un-mappable messages ────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO messages_quarantine (id, thread_id, sender_id, sender_role, recipient_id, body, sent_at, quarantine_reason)
        SELECT
            m.id, m.thread_id, m.sender_id, m.sender_role, m.recipient_id, m.body, m.sent_at,
            CASE
                WHEN m.sender_id IS NULL THEN 'missing sender_id'
                WHEN m.sender_role IS NULL AND m.recipient_id IS NULL AND m.thread_id IS NULL THEN 'missing all participant identifiers'
                WHEN m.sender_role NOT IN ('company', 'candidate') THEN 'unsupported sender role (' || coalesce(m.sender_role::text, 'null') || ')'
                ELSE 'participants could not be resolved to valid company and candidate profiles'
            END
        FROM messages m
        WHERE m.conversation_id IS NULL
    """))

    quarantined = conn.execute(
        sa.text("SELECT count(*) FROM messages_quarantine")
    ).scalar()

    # Delete quarantined rows from messages (they are safely in messages_quarantine)
    conn.execute(sa.text("""
        DELETE FROM messages WHERE conversation_id IS NULL
    """))

    # ── 6. Row-count assertion ────────────────────────────────────────
    remaining = conn.execute(
        sa.text("SELECT count(*) FROM messages")
    ).scalar()

    if remaining + quarantined != original_count:
        raise RuntimeError(
            f"Row-count mismatch: messages({remaining}) + quarantine({quarantined}) "
            f"= {remaining + quarantined}, expected {original_count}. "
            "Rolling back to preserve data."
        )

    # ── 7. Enforce NOT NULL and add FK + index on conversation_id ─────
    op.alter_column(
        "messages",
        "conversation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_messages_conversation_id",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── 8. Keep thread_id and recipient_id (expand phase) ─────────────
    # These columns are NOT dropped here. A separate contract migration
    # can drop them once the new schema is confirmed stable.


def downgrade() -> None:
    import os
    if os.getenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() not in ("1", "true", "yes"):
        raise RuntimeError(
            "Refusing to execute destructive downgrade: reverting conversation model will drop "
            "conversations table and revert to thread_id-based messaging. This is a major schema "
            "change even though quarantined messages are restored. If this is intentional in a local "
            "test, set ALLOW_DESTRUCTIVE_DOWNGRADE=1. In production, rollback must be performed via "
            "database snapshot restore."
        )
    # 1. Remove FK and index on conversation_id
    op.drop_constraint("fk_messages_conversation_id", "messages", type_="foreignkey")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")

    # 2. Drop new columns before restoring quarantined messages to avoid NOT NULL violation
    op.drop_column("messages", "read_at")
    op.drop_column("messages", "conversation_id")

    # 3. Restore quarantined messages back into the messages table
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO messages (id, thread_id, sender_id, sender_role, recipient_id, body, sent_at)
        SELECT id, thread_id, sender_id, sender_role, recipient_id, body, sent_at
        FROM messages_quarantine
        ON CONFLICT (id) DO NOTHING
    """))

    # 4. Drop quarantine and conversations tables
    op.drop_table("messages_quarantine")
    op.drop_index(op.f("ix_conversations_company_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_candidate_id"), table_name="conversations")
    op.drop_table("conversations")
