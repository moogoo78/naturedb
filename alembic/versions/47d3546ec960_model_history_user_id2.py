"""model-history-user-id2

Revision ID: 47d3546ec960
Revises: 541700092a8e
Create Date: 2023-12-03 18:49:05.753332

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '47d3546ec960'
down_revision = '541700092a8e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('model_history', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'model_history', 'user', ['user_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'model_history', type_='foreignkey')
    op.drop_column('model_history', 'user_id')
    # ### end Alembic commands ###
