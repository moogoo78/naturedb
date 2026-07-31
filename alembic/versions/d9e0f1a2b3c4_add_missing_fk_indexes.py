"""add missing FK indexes on taxon_relation and unit

Revision ID: d9e0f1a2b3c4
Revises: f7e8d9c0a1b2
Create Date: 2026-07-31 04:10:00.000000

PostgreSQL does not create indexes for foreign keys automatically, so these
three FK columns were only ever reachable by sequential scan:

  - taxon_relation.parent_id
  - taxon_relation.child_id
  - unit.record_id

taxon_relation is a closure table: every ancestry walk filters on parent_id or
child_id. On production this produced 13.1M sequential scans against 709k rows
(vs 608k index scans, a number that never moved), which pinned the DB CPU and
exhausted the instance's burst credits.

Built with CREATE INDEX CONCURRENTLY so the build takes no write lock -- `unit`
is written continuously by the admin edit path. That requires running outside a
transaction, hence the autocommit_block. statement_timeout is cleared for the
session because production sets a 30s cap that would otherwise kill the build
partway and leave an INVALID index behind.
"""
from alembic import op


revision = 'd9e0f1a2b3c4'
down_revision = 'f7e8d9c0a1b2'
branch_labels = None
depends_on = None


# (index name, table, column) -- names match SQLAlchemy's default
# ix_<table>_<column> so autogenerate stays quiet about them.
INDEXES = [
    ('ix_taxon_relation_parent_id', 'taxon_relation', 'parent_id'),
    ('ix_taxon_relation_child_id', 'taxon_relation', 'child_id'),
    ('ix_unit_record_id', 'unit', 'record_id'),
]


def upgrade():
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        for name, table, column in INDEXES:
            # IF NOT EXISTS: some environments may already have these applied
            # by hand during the incident.
            op.execute(
                f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} '
                f'ON {table} ({column})'
            )


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        for name, _table, _column in INDEXES:
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')
