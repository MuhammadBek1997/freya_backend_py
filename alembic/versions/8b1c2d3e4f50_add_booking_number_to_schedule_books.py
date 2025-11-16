"""add booking_number to schedule_books

Revision ID: 8b1c2d3e4f50
Revises: 4ceed921d88b
Create Date: 2025-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import secrets
from datetime import date


# revision identifiers, used by Alembic.
revision: str = '8b1c2d3e4f50'
down_revision: Union[str, None] = '4ceed921d88b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _gen_number(day: date, existing: set[str]) -> str:
    base = f"BOOK-{day.strftime('%Y%m%d')}"
    while True:
        suffix = secrets.token_hex(4).upper()
        number = f"{base}-{suffix}"
        if number not in existing:
            existing.add(number)
            return number


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'schedule_books' in tables:
        cols = {c['name'] for c in inspector.get_columns('schedule_books')}
        if 'booking_number' not in cols:
            op.add_column('schedule_books', sa.Column('booking_number', sa.String(length=50), nullable=True))
            op.create_unique_constraint('uq_schedule_books_booking_number', 'schedule_books', ['booking_number'])

        # Backfill booking_number for existing rows
        existing_numbers: set[str] = set()
        result = bind.execute(sa.text("SELECT id, time, booking_number FROM schedule_books"))
        rows = result.fetchall()
        for row in rows:
            bn = row.booking_number if hasattr(row, 'booking_number') else None
            if bn:
                existing_numbers.add(bn)
                continue
            day = row.time or date.today()
            number = _gen_number(day, existing_numbers)
            bind.execute(
                sa.text("UPDATE schedule_books SET booking_number = :bn WHERE id = :id"),
                {"bn": number, "id": row.id},
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'schedule_books' in tables:
        cols = {c['name'] for c in inspector.get_columns('schedule_books')}
        if 'booking_number' in cols:
            op.drop_constraint('uq_schedule_books_booking_number', 'schedule_books', type_='unique')
            op.drop_column('schedule_books', 'booking_number')