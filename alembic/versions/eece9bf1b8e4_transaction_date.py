"""transaction-date

Revision ID: eece9bf1b8e4
Revises: 902ead9f65ec
Create Date: 2023-07-21 07:55:20.879154

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eece9bf1b8e4'
down_revision = '902ead9f65ec'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('date_text', sa.String(length=500), nullable=True))
    op.add_column('transaction', sa.Column('agreed_end_date', sa.Date(), nullable=True))
    op.add_column('transaction', sa.Column('actual_end_date', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transaction', 'actual_end_date')
    op.drop_column('transaction', 'agreed_end_date')
    op.drop_column('transaction', 'date_text')
    # ### end Alembic commands ###