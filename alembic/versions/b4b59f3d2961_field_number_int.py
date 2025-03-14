"""field-number-int

Revision ID: b4b59f3d2961
Revises: 334ff7172057
Create Date: 2025-01-01 03:03:35.288398

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'b4b59f3d2961'
down_revision = '334ff7172057'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('record', sa.Column('field_number_int', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_record_field_number_int'), 'record', ['field_number_int'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_record_field_number_int'), table_name='record')
    op.drop_column('record', 'field_number_int')
    # ### end Alembic commands ###
