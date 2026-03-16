"""add coordinate_uncertainty_in_meters to record

Revision ID: 7b2e4c91a3d8
Revises: 3f8a1d92b047
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b2e4c91a3d8'
down_revision = '3f8a1d92b047'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('record',
                  sa.Column('coordinate_uncertainty_in_meters', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade():
    op.drop_column('record', 'coordinate_uncertainty_in_meters')
