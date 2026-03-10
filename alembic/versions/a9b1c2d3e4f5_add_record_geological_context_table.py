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

    # Drop geo columns that were previously added directly to record
    # (from old migrations 3225bc4e3243 + f7e8d9c0b1a2, applied before this refactor)
    _geo_cols = [
        'earliest_geochronologic', 'earliest_geochronologic_prefix',
        'latest_geochronologic', 'latest_geochronologic_prefix',
        'lowest_biostratigraphic_zone', 'highest_biostratigraphic_zone',
        'lithostratigraphic_terms', 'geological_context_group',
        'formation', 'member', 'bed',
    ]
    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='record'")
    )}
    for col in _geo_cols:
        if col in existing:
            op.drop_column('record', col)


def downgrade():
    op.drop_table('record_geological_context')
    op.add_column('record', sa.Column('earliest_geochronologic', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_geochronologic_prefix', sa.String(length=50), nullable=True))
    op.add_column('record', sa.Column('latest_geochronologic', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_geochronologic_prefix', sa.String(length=50), nullable=True))
    op.add_column('record', sa.Column('lowest_biostratigraphic_zone', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('highest_biostratigraphic_zone', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('lithostratigraphic_terms', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('geological_context_group', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('formation', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('member', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('bed', sa.String(length=500), nullable=True))
