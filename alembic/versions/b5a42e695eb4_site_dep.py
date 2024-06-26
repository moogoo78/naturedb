"""site-dep

Revision ID: b5a42e695eb4
Revises: 318dcd16a600
Create Date: 2024-06-18 02:38:08.714498

"""
from alembic import op
import sqlalchemy as sa

import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'b5a42e695eb4'
down_revision = '318dcd16a600'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('site',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=True),
    sa.Column('name_en', sa.String(length=500), nullable=True),
    sa.Column('short_name', sa.String(length=500), nullable=True),
    sa.Column('code', sa.String(length=500), nullable=True),
    sa.Column('domain', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('organization', sa.Column('site_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'organization', 'site', ['site_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'organization', type_='foreignkey')
    op.drop_column('organization', 'site_id')
    op.drop_table('site')
    # ### end Alembic commands ###