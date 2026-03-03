"""Clear bad note_ru and note_en translations

Revision ID: c1d2e3f4a5b6
Revises: f7e6d5c4b3a2
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union
from sqlalchemy import inspect
from alembic import op


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'f7e6d5c4b3a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear potentially wrong note_ru and note_en values so they get re-generated
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('salons')]
    if 'note_ru' in columns and 'note_en' in columns:
        op.execute("UPDATE salons SET note_ru = NULL, note_en = NULL")


def downgrade() -> None:
    pass
