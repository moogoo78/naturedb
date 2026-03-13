"""add geological_context_formation lookup table and wire to record_geological_context

Revision ID: c4d5e6f7a8b9
Revises: a9b1c2d3e4f5
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'a9b1c2d3e4f5'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create the new lookup table
    op.create_table(
        'geological_context_formation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('name_zh', sa.String(length=500), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Add the FK column to record_geological_context
    op.add_column(
        'record_geological_context',
        sa.Column('formation_id', sa.Integer(), sa.ForeignKey('geological_context_formation.id'), nullable=True),
    )

    # 3. Drop the old free-text formation column
    op.drop_column('record_geological_context', 'formation')


def downgrade():
    # 1. Restore free-text formation column
    op.add_column(
        'record_geological_context',
        sa.Column('formation', sa.String(length=500), nullable=True),
    )

    # 2. Drop the FK column
    op.drop_column('record_geological_context', 'formation_id')

    # 3. Drop the lookup table
    op.drop_table('geological_context_formation')
