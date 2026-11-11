"""unit: index guid (TBIA ?occurrenceID=<ARK> lookup)

Revision ID: e5a7c9d1f3b4
Revises: d4f6a8c0e2b3
Create Date: 2026-11-11 13:00:00.000000

The TBIA feed publishes the ARK as occurrenceID and looks units up by it.
"""
from alembic import op


revision = 'e5a7c9d1f3b4'
down_revision = 'd4f6a8c0e2b3'
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY cannot run inside a transaction
    with op.get_context().autocommit_block():
        op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_unit_guid ON unit (guid)')


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_unit_guid')
