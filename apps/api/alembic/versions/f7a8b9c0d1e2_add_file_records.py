"""Add file_records table for authenticated file serving

Revision ID: f7a8b9c0d1e2
Revises: e6c7d8e9f0a1
Create Date: 2026-10-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7a8b9c0d1e2'
down_revision = 'e6c7d8e9f0a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safely create enum via raw SQL IF NOT EXISTS
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE file_category AS ENUM ('photo', 'document', 'logo'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    file_category_enum = postgresql.ENUM('photo', 'document', 'logo', name='file_category', create_type=False)

    op.create_table(
        'file_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', file_category_enum, nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('original_filename', sa.String(length=512), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_file_records_owner_id'), 'file_records', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_file_records_owner_id'), table_name='file_records')
    op.drop_table('file_records')
    op.execute("DROP TYPE IF EXISTS file_category")
