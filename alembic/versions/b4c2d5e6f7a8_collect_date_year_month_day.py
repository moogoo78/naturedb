"""add collect_date_year_month_day

Revision ID: b4c2d5e6f7a8
Revises: a3f1c2d4e5b6
Create Date: 2026-04-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c2d5e6f7a8'
down_revision = 'a3f1c2d4e5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('record', sa.Column('collect_date_year', sa.Integer(), nullable=True))
    op.add_column('record', sa.Column('collect_date_month', sa.Integer(), nullable=True))
    op.add_column('record', sa.Column('collect_date_day', sa.Integer(), nullable=True))

    # Populate from existing collect_date
    op.execute("""
        UPDATE record
        SET collect_date_year = EXTRACT(YEAR FROM collect_date)::integer,
            collect_date_month = EXTRACT(MONTH FROM collect_date)::integer,
            collect_date_day = EXTRACT(DAY FROM collect_date)::integer
        WHERE collect_date IS NOT NULL
    """)


def downgrade():
    op.drop_column('record', 'collect_date_day')
    op.drop_column('record', 'collect_date_month')
    op.drop_column('record', 'collect_date_year')
