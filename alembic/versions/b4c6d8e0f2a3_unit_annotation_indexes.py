"""index unit_annotation for lookups by unit and by (type, value)

Revision ID: b4c6d8e0f2a3
Revises: a3b5c7d9e1f2
Create Date: 2026-10-16 10:00:00.000000

unit_annotation only had its primary key. Loading a unit's annotations
scanned the whole table, and so did filtering units by a custom field
(`annotations` in the /api/v1/units filter), which runs one
EXISTS (... annotation_type_id = ? AND value IN (...)) per field.
"""
from alembic import op


revision = 'b4c6d8e0f2a3'
down_revision = 'a3b5c7d9e1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('CREATE INDEX IF NOT EXISTS ix_unit_annotation_unit_id ON unit_annotation (unit_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_unit_annotation_type_value ON unit_annotation (annotation_type_id, value)')


def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_unit_annotation_type_value')
    op.execute('DROP INDEX IF EXISTS ix_unit_annotation_unit_id')
