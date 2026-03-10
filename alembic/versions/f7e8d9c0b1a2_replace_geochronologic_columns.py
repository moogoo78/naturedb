"""replace 10 geochronologic columns with 2 generic fields

Revision ID: a1b2c3d4e5f6
Revises: 3225bc4e3243
Create Date: 2026-03-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7e8d9c0b1a2'
down_revision = '3225bc4e3243'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('record', sa.Column('earliest_geochronologic', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_geochronologic_prefix', sa.String(length=50), nullable=True))
    op.add_column('record', sa.Column('latest_geochronologic', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_geochronologic_prefix', sa.String(length=50), nullable=True))

    op.drop_column('record', 'earliest_eon_or_lowest_eonothem')
    op.drop_column('record', 'latest_eon_or_highest_eonothem')
    op.drop_column('record', 'earliest_era_or_lowest_erathem')
    op.drop_column('record', 'latest_era_or_highest_erathem')
    op.drop_column('record', 'earliest_period_or_lowest_system')
    op.drop_column('record', 'latest_period_or_highest_system')
    op.drop_column('record', 'earliest_epoch_or_lowest_series')
    op.drop_column('record', 'latest_epoch_or_highest_series')
    op.drop_column('record', 'earliest_age_or_lowest_stage')
    op.drop_column('record', 'latest_age_or_highest_stage')


def downgrade():
    op.add_column('record', sa.Column('earliest_eon_or_lowest_eonothem', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_eon_or_highest_eonothem', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_era_or_lowest_erathem', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_era_or_highest_erathem', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_period_or_lowest_system', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_period_or_highest_system', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_epoch_or_lowest_series', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_epoch_or_highest_series', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('earliest_age_or_lowest_stage', sa.String(length=500), nullable=True))
    op.add_column('record', sa.Column('latest_age_or_highest_stage', sa.String(length=500), nullable=True))

    op.drop_column('record', 'earliest_geochronologic')
    op.drop_column('record', 'earliest_geochronologic_prefix')
    op.drop_column('record', 'latest_geochronologic')
    op.drop_column('record', 'latest_geochronologic_prefix')
