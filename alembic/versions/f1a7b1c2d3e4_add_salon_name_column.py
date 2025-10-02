"""Add salon_name to salons table; backfill and enforce NOT NULL

Revision ID: f1a7b1c2d3e4
Revises: ca2d6e65fab6
Create Date: 2025-10-02 12:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a7b1c2d3e4'
down_revision: Union[str, None] = 'ca2d6e65fab6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure salons.salon_name exists and is NOT NULL.

    On some environments, the `salons` table may have been created
    without the `salon_name` column. This migration adds the column,
    attempts to backfill from legacy `name` if present, and then
    enforces NOT NULL to match the model.
    """
    bind = op.get_bind()

    # Check if column already exists
    exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'salons'
              AND column_name = 'salon_name'
            LIMIT 1
            """
        )
    ).scalar()

    if not exists:
        # Add column as nullable first
        op.add_column('salons', sa.Column('salon_name', sa.String(length=200), nullable=True))

        # If legacy column `name` exists, backfill from it
        name_exists = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'salons'
                  AND column_name = 'name'
                LIMIT 1
                """
            )
        ).scalar()

        if name_exists:
            bind.execute(sa.text("UPDATE salons SET salon_name = name WHERE salon_name IS NULL"))

        # Fallback: ensure no NULLs remain before setting NOT NULL
        bind.execute(sa.text("UPDATE salons SET salon_name = COALESCE(salon_name, 'Unnamed Salon')"))

        # Enforce NOT NULL to align with ORM model
        op.alter_column('salons', 'salon_name', existing_type=sa.String(length=200), nullable=False)


def downgrade() -> None:
    # Make column nullable before drop in case of constraints
    try:
        op.alter_column('salons', 'salon_name', existing_type=sa.String(length=200), nullable=True)
    except Exception:
        # If column doesn't exist or cannot be altered, proceed to drop attempt
        pass

    # Drop the column (safe even if it doesn't exist depending on DB)
    try:
        op.drop_column('salons', 'salon_name')
    except Exception:
        # Ignore drop errors in downgrade to avoid breaking rollback in heterogeneous schemas
        pass