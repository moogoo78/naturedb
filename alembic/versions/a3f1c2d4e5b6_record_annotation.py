"""record-annotation

Revision ID: a3f1c2d4e5b6
Revises: 2d3ac4882c24
Create Date: 2026-03-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f1c2d4e5b6'
down_revision = 'cf68a46997e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('record_annotation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=True),
    sa.Column('value', sa.String(length=500), nullable=True),
    sa.Column('annotation_type_id', sa.Integer(), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['annotation_type_id'], ['annotation_type.id'], ),
    sa.ForeignKeyConstraint(['record_id'], ['record.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('record_annotation')
