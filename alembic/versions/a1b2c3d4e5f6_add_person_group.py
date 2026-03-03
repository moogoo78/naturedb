"""add person_group and person_group_map tables

Revision ID: a1b2c3d4e5f6
Revises: f5ecbe5589ed
Create Date: 2026-03-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f5ecbe5589ed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'person_group',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(500), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'person_group_map',
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('person.id'), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('person_group.id'), primary_key=True),
    )


def downgrade():
    op.drop_table('person_group_map')
    op.drop_table('person_group')
