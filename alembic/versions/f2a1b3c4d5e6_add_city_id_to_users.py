"""add city_id to users

Revision ID: f2a1b3c4d5e6
Revises: b1c2d3e4f5a6_add_logo_to_salons
Create Date: 2025-10-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a1b3c4d5e6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('city_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('users', 'city_id')