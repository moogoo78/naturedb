"""taxon: index (tree_id, canonical_name) for reference-tree name lookup

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
Create Date: 2026-11-04 12:00:00.000000

The public specimen page matches the record's taxon by canonical name inside
a reference tree (e.g. TaiCOL) on every view; without this it is a seq scan
over the whole taxon table.
"""
from alembic import op


revision = 'c3e5a7b9d1f2'
down_revision = 'b2d4f6a8c0e1'
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY cannot run inside a transaction
    with op.get_context().autocommit_block():
        op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_taxon_tree_id_canonical_name '
                   'ON taxon (tree_id, canonical_name)')


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_taxon_tree_id_canonical_name')
