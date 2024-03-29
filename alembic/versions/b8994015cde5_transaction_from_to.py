"""transaction-from-to

Revision ID: b8994015cde5
Revises: eece9bf1b8e4
Create Date: 2023-07-21 09:26:53.516461

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8994015cde5'
down_revision = 'eece9bf1b8e4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('transaction_from', sa.String(length=500), nullable=True))
    op.add_column('transaction', sa.Column('transaction_to', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transaction', 'transaction_to')
    op.drop_column('transaction', 'transaction_from')
    # ### end Alembic commands ###
