"""migrate collect_date_text to year/month/day columns

Revision ID: c5d3e6f7a8b9
Revises: b4c2d5e6f7a8
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c5d3e6f7a8b9'
down_revision = 'b4c2d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Full date: YYYY-MM-DD or YYYY/MM/DD
    op.execute("""
        UPDATE record
        SET collect_date_year = substring(collect_date_text from '^\\d{4}')::integer,
            collect_date_month = substring(collect_date_text from '^\\d{4}[-/](\\d{1,2})')::integer,
            collect_date_day = substring(collect_date_text from '^\\d{4}[-/]\\d{1,2}[-/](\\d{1,2})$')::integer,
            collect_date = collect_date_text::date
        WHERE collect_date IS NULL
          AND collect_date_text ~ '^\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}$'
    """)

    # 2. Year-month: YYYY-MM or YYYY/MM
    op.execute("""
        UPDATE record
        SET collect_date_year = substring(collect_date_text from '^\\d{4}')::integer,
            collect_date_month = substring(collect_date_text from '^\\d{4}[-/](\\d{1,2})$')::integer
        WHERE collect_date IS NULL
          AND collect_date_year IS NULL
          AND collect_date_text ~ '^\\d{4}[-/]\\d{1,2}$'
    """)

    # 3. Year only: YYYY
    op.execute("""
        UPDATE record
        SET collect_date_year = collect_date_text::integer
        WHERE collect_date IS NULL
          AND collect_date_year IS NULL
          AND collect_date_text ~ '^\\d{4}$'
    """)


def downgrade():
    # Clear values that were populated from collect_date_text
    # (only rows where collect_date is still NULL, meaning they came from text parsing)
    op.execute("""
        UPDATE record
        SET collect_date_year = NULL,
            collect_date_month = NULL,
            collect_date_day = NULL
        WHERE collect_date IS NULL
          AND collect_date_text IS NOT NULL
          AND collect_date_year IS NOT NULL
    """)
