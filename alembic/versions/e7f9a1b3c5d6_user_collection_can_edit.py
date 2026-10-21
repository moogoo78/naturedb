"""user_collection.can_edit separates viewing a collection from editing it

Revision ID: e7f9a1b3c5d6
Revises: d6e8f0a2b4c5
Create Date: 2026-10-21 10:00:00.000000

The greenhouse editor must see HAST (collection 1: the greenhouse units' records
and the client's HAST Begoniaceae source) but edit only collection 9. Existing
rows default to true, i.e. unchanged.
"""
from alembic import op


revision = 'e7f9a1b3c5d6'
down_revision = 'd6e8f0a2b4c5'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('ALTER TABLE user_collection ADD COLUMN can_edit BOOLEAN NOT NULL DEFAULT true')


def downgrade():
    op.execute('ALTER TABLE user_collection DROP COLUMN can_edit')
