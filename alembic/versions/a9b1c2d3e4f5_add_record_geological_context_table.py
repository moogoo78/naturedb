"""add record_geological_context table

Revision ID: a9b1c2d3e4f5
Revises: e5f6a7b8c9d0
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9b1c2d3e4f5'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'record_geological_context',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('earliest_geochronologic', sa.String(length=500), nullable=True),
        sa.Column('earliest_geochronologic_prefix', sa.String(length=50), nullable=True),
        sa.Column('latest_geochronologic', sa.String(length=500), nullable=True),
        sa.Column('latest_geochronologic_prefix', sa.String(length=50), nullable=True),
        sa.Column('lowest_biostratigraphic_zone', sa.String(length=500), nullable=True),
        sa.Column('highest_biostratigraphic_zone', sa.String(length=500), nullable=True),
        sa.Column('lithostratigraphic_terms', sa.String(length=500), nullable=True),
        sa.Column('geological_context_group', sa.String(length=500), nullable=True),
        sa.Column('formation', sa.String(length=500), nullable=True),
        sa.Column('member', sa.String(length=500), nullable=True),
        sa.Column('bed', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['record_id'], ['record.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id'),
    )


def downgrade():
    op.drop_table('record_geological_context')
