"""tune autovacuum thresholds on the large tables

Revision ID: a3b5c7d9e1f2
Revises: d9e0f1a2b3c4
Create Date: 2026-07-31 04:30:00.000000

The stock autovacuum scale factors are percentages of table size, so they get
progressively worse as a table grows:

  analyze at  50 + 0.10 * n_live_tup
  vacuum  at  50 + 0.20 * n_live_tup

On `unit` (183k rows) that means autoanalyze only fires after ~18,400
modifications and autovacuum after ~36,700 dead tuples. Each run is therefore
large and slow, and on a CPU-constrained host a run that never finishes leaves
the table permanently stale -- `unit` had no recorded vacuum or analyze *ever*,
which is how the planner ended up estimating 1,374 rows against 183,284 actual
and choosing sequential scans everywhere (see revision d9e0f1a2b3c4).

Lowering the scale factors makes autovacuum fire earlier and do less work per
run, so runs actually complete:

  analyze at  50 + 0.02 * n_live_tup   (unit: ~3,700)
  vacuum  at  50 + 0.05 * n_live_tup   (unit: ~9,200)

I/O on this host is idle (wa ~0), so the extra passes are cheap; the scarce
resource is CPU, and stale statistics cost far more CPU than vacuuming does.

These are table storage parameters, so they live with the schema and apply to
every environment. Alembic's autogenerate does not compare storage parameters,
so this will not show up as drift in either direction.
"""
from alembic import op


revision = 'a3b5c7d9e1f2'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


TABLES = ['unit', 'record', 'taxon', 'taxon_relation']

SETTINGS = {
    'autovacuum_analyze_scale_factor': '0.02',
    'autovacuum_vacuum_scale_factor': '0.05',
}


def upgrade():
    # ALTER TABLE ... SET (...) is metadata-only and instantaneous, but it
    # still needs ACCESS EXCLUSIVE. Without a lock_timeout the request queues
    # behind any in-flight query and blocks every subsequent one on that table.
    # Fail fast instead of building a queue on a live site.
    op.execute('SET lock_timeout = \'5s\'')
    params = ', '.join(f'{k} = {v}' for k, v in SETTINGS.items())
    for table in TABLES:
        op.execute(f'ALTER TABLE {table} SET ({params})')


def downgrade():
    op.execute('SET lock_timeout = \'5s\'')
    params = ', '.join(SETTINGS)
    for table in TABLES:
        op.execute(f'ALTER TABLE {table} RESET ({params})')
