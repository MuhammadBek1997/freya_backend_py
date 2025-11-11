"""merge heads

Revision ID: 7f9a6c1b2d34
Revises: d1e2f3a4b5c6, a7b8c9d0e1f2
Create Date: 2025-11-11 06:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7f9a6c1b2d34"
down_revision = ("d1e2f3a4b5c6", "a7b8c9d0e1f2")
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge point, no operations are required.
    pass


def downgrade():
    # Downgrade does not split branches; usually left as pass.
    pass