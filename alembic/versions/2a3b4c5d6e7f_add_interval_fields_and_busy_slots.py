"""add end_time/duration to appointments and busy_slots table

Revision ID: 2a3b4c5d6e7f
Revises: 1f0a2b3c4d5e
Create Date: 2025-11-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "2a3b4c5d6e7f"
down_revision = "1f0a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('appointments')]

    # appointments jadvaliga yangi ustunlar (faqat yo‘q bo‘lsa)
    if 'end_time' not in columns:
        op.add_column("appointments", sa.Column("end_time", sa.Time(), nullable=True))
    if 'duration_minutes' not in columns:
        op.add_column("appointments", sa.Column("duration_minutes", sa.Integer(), nullable=True))

    # indexni faqat mavjud bo‘lmasa qo‘shamiz
    existing_indexes = [ix['name'] for ix in inspector.get_indexes('appointments')]
    if 'ix_appointments_emp_date' not in existing_indexes:
        op.create_index(
            "ix_appointments_emp_date",
            "appointments",
            ["employee_id", "application_date"],
            unique=False
        )

    # busy_slots jadvali (faqat yo‘q bo‘lsa yaratiladi)
    if not inspector.has_table("busy_slots"):
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
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('appointments')]

    # busy_slots jadvalini qaytarish
    if inspector.has_table("busy_slots"):
        op.drop_index("ix_busy_slots_emp_date", table_name="busy_slots")
        op.drop_table("busy_slots")

    # appointments ustunlarini qaytarish (faqat mavjud bo‘lsa)
    existing_indexes = [ix['name'] for ix in inspector.get_indexes('appointments')]
    if 'ix_appointments_emp_date' in existing_indexes:
        op.drop_index("ix_appointments_emp_date", table_name="appointments")

    if 'duration_minutes' in columns:
        op.drop_column("appointments", "duration_minutes")

    if 'end_time' in columns:
        op.drop_column("appointments", "end_time")
