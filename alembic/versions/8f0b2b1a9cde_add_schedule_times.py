"""add start_time and end_time to schedules

Revision ID: 8f0b2b1a9cde
Revises: 3c29f90b4d64
Create Date: 2025-10-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f0b2b1a9cde'
down_revision = '3c29f90b4d64'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'schedules' in tables:
        columns = {c['name'] for c in inspector.get_columns('schedules')}
        if 'start_time' not in columns:
            op.add_column('schedules', sa.Column('start_time', sa.Time(), nullable=True))
        if 'end_time' not in columns:
            op.add_column('schedules', sa.Column('end_time', sa.Time(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'schedules' in tables:
        columns = {c['name'] for c in inspector.get_columns('schedules')}
        if 'end_time' in columns:
            op.drop_column('schedules', 'end_time')
        if 'start_time' in columns:
            op.drop_column('schedules', 'start_time')