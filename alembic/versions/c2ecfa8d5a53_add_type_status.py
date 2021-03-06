"""add type_status

Revision ID: c2ecfa8d5a53
Revises: c38fdb886075
Create Date: 2022-01-22 08:32:58.057620

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2ecfa8d5a53'
down_revision = 'c38fdb886075'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('identification', sa.Column('type_status', sa.String(length=50), nullable=True))
    op.add_column('identification', sa.Column('type_text', sa.String(length=1000), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('identification', 'type_text')
    op.drop_column('identification', 'type_status')
    # ### end Alembic commands ###
