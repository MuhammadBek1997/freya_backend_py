"""Add note_uz, note_ru, note_en to salons

Revision ID: f7e6d5c4b3a2
Revises: b5c6d7e8f9a0
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union
from sqlalchemy import inspect
from alembic import op
import sqlalchemy as sa


revision: str = 'f7e6d5c4b3a2'
down_revision: Union[str, None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('salons')]

    if 'note_uz' not in existing_columns:
        op.add_column('salons', sa.Column('note_uz', sa.Text(), nullable=True))
        op.execute("UPDATE salons SET note_uz = note WHERE note IS NOT NULL AND note != ''")

    if 'note_ru' not in existing_columns:
        op.add_column('salons', sa.Column('note_ru', sa.Text(), nullable=True))

    if 'note_en' not in existing_columns:
        op.add_column('salons', sa.Column('note_en', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('salons', 'note_en')
    op.drop_column('salons', 'note_ru')
    op.drop_column('salons', 'note_uz')
