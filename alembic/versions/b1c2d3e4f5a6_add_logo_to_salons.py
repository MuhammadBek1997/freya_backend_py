"""add logo column to salons

Revision ID: b1c2d3e4f5a6
Revises: 8f0b2b1a9cde
Create Date: 2025-10-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = '8f0b2b1a9cde'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'salons' in tables:
        columns = {c['name'] for c in inspector.get_columns('salons')}
        if 'logo' not in columns:
            op.add_column('salons', sa.Column('logo', sa.String(length=500), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'salons' in tables:
        columns = {c['name'] for c in inspector.get_columns('salons')}
        if 'logo' in columns:
            op.drop_column('salons', 'logo')