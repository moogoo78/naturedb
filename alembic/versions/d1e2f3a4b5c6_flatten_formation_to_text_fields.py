"""flatten formation: drop FK, add formation + formation_en text columns

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop the FK column from record_geological_context
    op.drop_column('record_geological_context', 'formation_id')

    # 2. Add free-text formation columns
    op.add_column(
        'record_geological_context',
        sa.Column('formation', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'record_geological_context',
        sa.Column('formation_en', sa.String(length=500), nullable=True),
    )

    # 3. Drop the now-unused lookup table
    op.drop_table('geological_context_formation')


def downgrade():
    # 1. Recreate the lookup table
    op.create_table(
        'geological_context_formation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('name_zh', sa.String(length=500), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Drop free-text columns
    op.drop_column('record_geological_context', 'formation_en')
    op.drop_column('record_geological_context', 'formation')

    # 3. Restore the FK column
    op.add_column(
        'record_geological_context',
        sa.Column('formation_id', sa.Integer(), sa.ForeignKey('geological_context_formation.id'), nullable=True),
    )
