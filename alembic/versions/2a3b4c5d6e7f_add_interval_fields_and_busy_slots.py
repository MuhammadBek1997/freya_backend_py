"""add end_time/duration to appointments and busy_slots table

Revision ID: 2a3b4c5d6e7f
Revises: 1f0a2b3c4d5e
Create Date: 2025-11-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2a3b4c5d6e7f"
down_revision = "1f0a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    # appointments jadvaliga yangi ustunlar
    op.add_column("appointments", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("appointments", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    # tez-tez so'raladigan filtrlash uchun index
    op.create_index("ix_appointments_emp_date", "appointments", ["employee_id", "application_date"], unique=False)

    # busy_slots jadvali
    op.create_table(
        "busy_slots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_busy_slots_emp_date", "busy_slots", ["employee_id", "date"], unique=False)


def downgrade():
    # busy_slots jadvalini qaytarish
    op.drop_index("ix_busy_slots_emp_date", table_name="busy_slots")
    op.drop_table("busy_slots")

    # appointments ustunlarini qaytarish
    op.drop_index("ix_appointments_emp_date", table_name="appointments")
    op.drop_column("appointments", "duration_minutes")
    op.drop_column("appointments", "end_time")