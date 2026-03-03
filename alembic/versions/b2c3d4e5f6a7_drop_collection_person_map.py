"""drop collection_person_map table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('collection_person_map')


def downgrade():
    op.create_table(
        'collection_person_map',
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('collection.id'), primary_key=True),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('person.id'), primary_key=True),
    )
