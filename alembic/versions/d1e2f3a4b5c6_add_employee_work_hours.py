"""add work_start_time and work_end_time to employees

Revision ID: d1e2f3a4b5c6
Revises: 58a96ab93c9b
Create Date: 2025-11-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = '58a96ab93c9b'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'employees' in tables:
        columns = {c['name'] for c in inspector.get_columns('employees')}
        if 'work_start_time' not in columns:
            op.add_column('employees', sa.Column('work_start_time', sa.String(length=5), nullable=True))
        if 'work_end_time' not in columns:
            op.add_column('employees', sa.Column('work_end_time', sa.String(length=5), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'employees' in tables:
        columns = {c['name'] for c in inspector.get_columns('employees')}
        if 'work_end_time' in columns:
            op.drop_column('employees', 'work_end_time')
        if 'work_start_time' in columns:
            op.drop_column('employees', 'work_start_time')