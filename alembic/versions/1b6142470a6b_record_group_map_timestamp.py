"""record-group-map-timestamp

Revision ID: 1b6142470a6b
Revises: 7862fd6c810e
Create Date: 2024-12-10 10:00:30.968886

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = '1b6142470a6b'
down_revision = '7862fd6c810e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('record_group_map', sa.Column('created', sa.DateTime(), nullable=True))
    op.add_column('record_group_map', sa.Column('updated', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('record_group_map', 'updated')
    op.drop_column('record_group_map', 'created')
    # ### end Alembic commands ###