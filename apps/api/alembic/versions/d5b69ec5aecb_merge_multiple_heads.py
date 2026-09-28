"""merge multiple heads

Revision ID: d5b69ec5aecb
Revises: a1b2c3d4e5f6, b3c4d5e6f7a8
Create Date: 2026-09-28 18:57:11.185687
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd5b69ec5aecb'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'b3c4d5e6f7a8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
