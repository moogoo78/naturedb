"""unit-pid

Revision ID: 5239ef1d08b2
Revises: 47d3546ec960
Create Date: 2023-12-11 09:19:54.385857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5239ef1d08b2'
down_revision = '47d3546ec960'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('unit', sa.Column('persistent_idenfier', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('unit', 'persistent_idenfier')
    # ### end Alembic commands ###
