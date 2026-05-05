"""ai-label-extractor: add Person.preferences_json + UnitVerbatim AI prompt-version index

Revision ID: c7d4e8a1b2f3
Revises: b3c4d5e6f7a8
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'c7d4e8a1b2f3'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'person',
        sa.Column(
            'preferences_json',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE INDEX ix_unit_verbatim_ai_prompt_version "
        "ON unit_verbatim (unit_id, ((source_data->>'prompt_version'))) "
        "WHERE source_type = 'ai'"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_unit_verbatim_ai_prompt_version")
    op.drop_column('person', 'preferences_json')
