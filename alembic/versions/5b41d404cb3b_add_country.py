"""add-country

Revision ID: 5b41d404cb3b
Revises: 675f3d3e99af
Create Date: 2024-02-23 19:31:48.163498

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
import geoalchemy2

# revision identifiers, used by Alembic.
revision = '5b41d404cb3b'
down_revision = '675f3d3e99af'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('country',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name_en', sa.String(length=500), nullable=True),
    sa.Column('name_zh', sa.String(length=500), nullable=True),
    sa.Column('continent', sa.String(length=500), nullable=True),
    sa.Column('iso3166_1', sa.String(length=2), nullable=True),
    sa.Column('iso3', sa.String(length=3), nullable=True),
    sa.Column('status', sa.String(length=500), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('country')
    # ### end Alembic commands ###
