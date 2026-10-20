"""user_collection limits a user to some of the site's collections

Revision ID: d6e8f0a2b4c5
Revises: c5d7e9f1a3b4
Create Date: 2026-10-20 10:00:00.000000

A user with no rows here keeps the whole site (User.collection_ids falls back
to site.collection_ids), so existing users are unaffected.
"""
from alembic import op


revision = 'd6e8f0a2b4c5'
down_revision = 'c5d7e9f1a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('''
        CREATE TABLE user_collection (
            user_id INTEGER NOT NULL REFERENCES "user" (id) ON DELETE CASCADE,
            collection_id INTEGER NOT NULL REFERENCES collection (id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, collection_id)
        )
    ''')
    op.execute('CREATE INDEX ix_user_collection_collection_id ON user_collection (collection_id)')


def downgrade():
    op.execute('DROP TABLE IF EXISTS user_collection')
