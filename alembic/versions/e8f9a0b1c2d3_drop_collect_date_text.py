"""drop record.collect_date_text column

Revision ID: e8f9a0b1c2d3
Revises: d6e7f8a9b0c1
Create Date: 2026-04-25 00:00:00.000000

Data was migrated into collect_date_year/month/day by c5d3e6f7a8b9.
This migration removes the now-redundant text column.
"""
from alembic import op
import sqlalchemy as sa


revision = 'e8f9a0b1c2d3'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('record', 'collect_date_text')


def downgrade():
    op.add_column('record', sa.Column('collect_date_text', sa.String(length=500), nullable=True))
