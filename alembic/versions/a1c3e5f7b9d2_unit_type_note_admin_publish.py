"""unit.type_note splits into type_note_admin (hidden) and type_note_publish (public)

Revision ID: a1c3e5f7b9d2
Revises: e7f9a1b3c5d6
Create Date: 2026-10-21 12:00:00.000000

Existing type_note values must no longer be public, so the column is renamed
to type_note_admin (admin record form only). type_note_publish is new and
empty; it is what the public specimen page shows.
"""
from alembic import op


revision = 'a1c3e5f7b9d2'
down_revision = 'e7f9a1b3c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('ALTER TABLE unit RENAME COLUMN type_note TO type_note_admin')
    op.execute('ALTER TABLE unit ADD COLUMN type_note_publish VARCHAR(500)')


def downgrade():
    op.execute('ALTER TABLE unit DROP COLUMN type_note_publish')
    op.execute('ALTER TABLE unit RENAME COLUMN type_note_admin TO type_note')
