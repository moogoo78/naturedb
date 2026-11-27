"""unit: index ltrim(catalog_number, '0') for specimen URL lookup

Revision ID: f6b8d0e2a4c6
Revises: e5a7c9d1f3b4
Create Date: 2026-11-27 01:00:00.000000

_catalog_number_match() (app/helpers.py) filters on
ltrim(catalog_number, '0') so /specimens/HAST:61016 finds '061016'. The
plain ix_unit_catalog_number cannot serve that expression, so every
specimen page seq-scanned unit (185k rows, 479 MB). Under the
2026-11-26 crawl that exhausted the t3 CPU credits.
"""
from alembic import op


revision = 'f6b8d0e2a4c6'
down_revision = 'e5a7c9d1f3b4'
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY cannot run inside a transaction, and keeps the table
    # readable/writable while it builds. Production runs with
    # statement_timeout = 30s, which would kill the build partway.
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_unit_catalog_number_ltrim "
                   "ON unit (ltrim(catalog_number, '0'))")


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('SET statement_timeout = 0')
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_unit_catalog_number_ltrim')
