"""change profession column from varchar to json

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'employees' in tables:
        columns = {c['name']: c for c in inspector.get_columns('employees')}
        if 'profession' in columns:
            col_type = str(columns['profession']['type'])
            # Only migrate if column is NOT already JSON
            if 'json' not in col_type.lower():
                # Step 1: Convert existing string values to JSON arrays
                # e.g. "Стилист" -> '["Стилист"]'
                op.execute(
                    """
                    UPDATE employees
                    SET profession = CASE
                        WHEN profession IS NULL OR profession = '' THEN '[]'
                        WHEN profession LIKE '[%' THEN profession
                        ELSE '["' || replace(profession, '"', '\\"') || '"]'
                    END
                    """
                )

                # Step 2: Change column type from varchar to json
                op.execute(
                    """
                    ALTER TABLE employees
                    ALTER COLUMN profession TYPE json USING profession::json
                    """
                )

                # Step 3: Set default value
                op.execute(
                    """
                    ALTER TABLE employees
                    ALTER COLUMN profession SET DEFAULT '[]'::json
                    """
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'employees' in tables:
        # Convert back to varchar
        op.execute(
            """
            ALTER TABLE employees
            ALTER COLUMN profession TYPE varchar(100)
            USING CASE
                WHEN profession IS NULL THEN NULL
                ELSE profession::text
            END
            """
        )
