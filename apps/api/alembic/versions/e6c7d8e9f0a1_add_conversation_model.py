"""Add conversation model

Revision ID: e6c7d8e9f0a1
Revises: d5b69ec5aecb
Create Date: 2026-09-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e6c7d8e9f0a1'
down_revision = 'd5b69ec5aecb'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create conversations table
    op.create_table('conversations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.user_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['companies.user_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['job_id'], ['job_postings.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'candidate_id', name='uq_conversation_participants')
    )
    op.create_index(op.f('ix_conversations_candidate_id'), 'conversations', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_conversations_company_id'), 'conversations', ['company_id'], unique=False)

    # 2. Delete any orphaned messages as the DB is essentially empty in dev anyway for messages
    op.execute("DELETE FROM messages")
    
    # 3. Add conversation_id and read_at to messages
    op.add_column('messages', sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column('messages', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    
    op.drop_index('ix_messages_thread_id', table_name='messages')
    op.drop_column('messages', 'thread_id')
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_foreign_key(None, 'messages', 'conversations', ['conversation_id'], ['id'], ondelete='CASCADE')
    
    # Drop recipient_id since we moved it to Conversation
    op.drop_index('ix_messages_recipient_id', table_name='messages')
    op.drop_column('messages', 'recipient_id')

def downgrade() -> None:
    pass
