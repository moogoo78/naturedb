"""add formation_en to record_geological_context

Revision ID: 5cc2cedf7d7f
Revises: f41778c0817e
Create Date: 2026-03-13 06:57:05.072675

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = '5cc2cedf7d7f'
down_revision = 'f41778c0817e'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: Most operations from the original auto-generated migration are already
    # handled by earlier migrations (a9b1c2d3e4f5 through f41778c0817e).
    # Only the record_person.role drop is unique to this migration.
    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='record_person'")
    )}
    if 'role' in existing:
        op.drop_column('record_person', 'role')


def downgrade():
    op.add_column('record_person', sa.Column('role', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
