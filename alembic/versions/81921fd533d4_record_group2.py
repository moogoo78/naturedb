"""record-group2

Revision ID: 81921fd533d4
Revises: 7d75748250ef
Create Date: 2024-10-21 10:55:45.389374

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = '81921fd533d4'
down_revision = '7d75748250ef'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('record_group', sa.Column('name_en', sa.String(length=500), nullable=True))
    op.drop_column('record_group', 'group_type')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('record_group', sa.Column('group_type', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_column('record_group', 'name_en')
    # ### end Alembic commands ###