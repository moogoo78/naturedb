"""record-group-map

Revision ID: 7d75748250ef
Revises: 686394455b1e
Create Date: 2024-10-21 10:52:50.762487

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = '7d75748250ef'
down_revision = '686394455b1e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('record_group',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('collection_id', sa.Integer(), nullable=True),
    sa.Column('group_type', sa.String(length=50), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['collection.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('record_group_map',
    sa.Column('record_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['record_group.id'], ),
    sa.ForeignKeyConstraint(['record_id'], ['record.id'], ),
    sa.PrimaryKeyConstraint('record_id', 'group_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('record_group_map')
    op.drop_table('record_group')
    # ### end Alembic commands ###