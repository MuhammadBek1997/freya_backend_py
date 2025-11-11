"""add unique employee slot constraint

Revision ID: 1f0a2b3c4d5e
Revises: 95504429335c
Create Date: 2025-11-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1f0a2b3c4d5e"
down_revision = "95504429335c"
branch_labels = None
depends_on = None


def upgrade():
    # appointments jadvalida composite unique constraint
    op.create_unique_constraint(
        "uq_employee_slot",
        "appointments",
        ["employee_id", "application_date", "application_time"],
    )


def downgrade():
    op.drop_constraint("uq_employee_slot", "appointments", type_="unique")