"""Add work_hours, work_days, note to salons

Revision ID: a1b2c3d4e5f6
Revises: 5c64d54205e2
Create Date: 2026-01-26

"""
from typing import Sequence, Union
from sqlalchemy import inspect
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5c64d54205e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if 'salons' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('salons')]

        if 'work_hours' not in columns:
            op.add_column('salons', sa.Column('work_hours', sa.String(50), nullable=True))

        if 'work_days' not in columns:
            op.add_column('salons', sa.Column('work_days', sa.String(100), nullable=True))

        if 'note' not in columns:
            op.add_column('salons', sa.Column('note', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if 'salons' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('salons')]

        if 'work_hours' in columns:
            op.drop_column('salons', 'work_hours')

        if 'work_days' in columns:
            op.drop_column('salons', 'work_days')

        if 'note' in columns:
            op.drop_column('salons', 'note')
