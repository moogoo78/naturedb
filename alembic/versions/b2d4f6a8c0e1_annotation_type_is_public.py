"""annotation_type.is_public: opt-in visibility on the public specimen page

Revision ID: b2d4f6a8c0e1
Revises: a1c3e5f7b9d2
Create Date: 2026-10-27 12:00:00.000000

Annotation types carry internal flags too (validator issues, transcription
workflow), so every existing type stays hidden until an admin opts it in.
"""
from alembic import op


revision = 'b2d4f6a8c0e1'
down_revision = 'a1c3e5f7b9d2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('ALTER TABLE annotation_type ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT false')


def downgrade():
    op.execute('ALTER TABLE annotation_type DROP COLUMN is_public')
