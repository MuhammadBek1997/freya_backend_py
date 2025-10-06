"""add user_employee_contacts table

Revision ID: a7b8c9d0e1f2
Revises: f2a1b3c4d5e6
Create Date: 2025-10-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f2a1b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'user_employee_contacts' in tables:
        return

    op.create_table(
        'user_employee_contacts',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('employee_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'employee_id', name='uq_user_employee_contact'),
    )


def downgrade():
    op.drop_table('user_employee_contacts')