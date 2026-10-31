"""merge multiple heads

Revision ID: 43b4f33a0dcf
Revises: c7d8e9f0a1b2, g8h9i0j1k2l3
Create Date: 2026-10-31 17:24:17.710679
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '43b4f33a0dcf'
down_revision: Union[str, None] = ('c7d8e9f0a1b2', 'g8h9i0j1k2l3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
