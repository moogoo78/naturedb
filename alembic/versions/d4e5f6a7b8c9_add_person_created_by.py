"""add person.created_by column

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('person', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_foreign_key('person_created_by_fkey', 'person', 'user', ['created_by'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('person_created_by_fkey', 'person', type_='foreignkey')
    op.drop_column('person', 'created_by')
