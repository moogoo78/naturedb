"""infra

Revision ID: 4ae271900f9c
Revises: bafad5853ba5
Create Date: 2024-12-06 09:53:55.337830

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = '4ae271900f9c'
down_revision = 'bafad5853ba5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('taxon', sa.Column('infraspecific_epithet2', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('taxon', 'infraspecific_epithet2')
    # ### end Alembic commands ###