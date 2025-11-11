"""merge multiple heads

Revision ID: 95504429335c
Revises: 02f2f31cbf39, 7f9a6c1b2d34
Create Date: 2025-11-11 14:35:53.688815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95504429335c'
down_revision: Union[str, None] = ('02f2f31cbf39', '7f9a6c1b2d34')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
