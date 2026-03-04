"""drop person.site_id column

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('person_site_id_fkey', 'person', type_='foreignkey')
    op.drop_column('person', 'site_id')


def downgrade():
    op.add_column('person', sa.Column('site_id', sa.Integer(), nullable=True))
    op.create_foreign_key('person_site_id_fkey', 'person', 'site', ['site_id'], ['id'], ondelete='SET NULL')
