"""nam-nma

Revision ID: e4514c176578
Revises: 2d06cf9ce61d
Create Date: 2023-12-14 23:57:27.244060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4514c176578'
down_revision = '2d06cf9ce61d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization', sa.Column('ark_nma', sa.String(length=500), nullable=True))
    op.drop_column('organization', 'ark_nam')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization', sa.Column('ark_nam', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
    op.drop_column('organization', 'ark_nma')
    # ### end Alembic commands ###