"""taxon-author

Revision ID: 120c3695c90e
Revises: e4514c176578
Create Date: 2023-12-19 23:38:08.878299

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '120c3695c90e'
down_revision = 'e4514c176578'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('taxon', sa.Column('rank_abbr', sa.String(length=500), nullable=True))
    op.add_column('taxon', sa.Column('author_parenthesis', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('taxon', 'author_parenthesis')
    op.drop_column('taxon', 'rank_abbr')
    # ### end Alembic commands ###
