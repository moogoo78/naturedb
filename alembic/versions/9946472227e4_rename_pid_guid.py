"""rename-pid-guid

Revision ID: 9946472227e4
Revises: 11adeca71f0a
Create Date: 2023-12-11 17:34:35.943236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9946472227e4'
down_revision = '11adeca71f0a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('unit', sa.Column('guid', sa.String(length=500), nullable=True))
    op.drop_column('unit', 'persistent_identifier')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('unit', sa.Column('persistent_identifier', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
    op.drop_column('unit', 'guid')
    # ### end Alembic commands ###