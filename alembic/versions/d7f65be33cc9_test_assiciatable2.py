"""test-assiciatable2

Revision ID: d7f65be33cc9
Revises: f39056da6198
Create Date: 2022-03-28 08:03:58.789106

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7f65be33cc9'
down_revision = 'f39056da6198'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('association')
    op.drop_constraint('collection_named_area_collection_id_fkey', 'collection_named_area', type_='foreignkey')
    op.drop_constraint('collection_named_area_named_area_id_fkey', 'collection_named_area', type_='foreignkey')
    op.create_foreign_key(None, 'collection_named_area', 'collection', ['collection_id'], ['id'])
    op.create_foreign_key(None, 'collection_named_area', 'named_area', ['named_area_id'], ['id'])
    op.drop_column('collection_named_area', 'id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('collection_named_area', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.drop_constraint(None, 'collection_named_area', type_='foreignkey')
    op.drop_constraint(None, 'collection_named_area', type_='foreignkey')
    op.create_foreign_key('collection_named_area_named_area_id_fkey', 'collection_named_area', 'named_area', ['named_area_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('collection_named_area_collection_id_fkey', 'collection_named_area', 'collection', ['collection_id'], ['id'], ondelete='SET NULL')
    op.create_table('association',
    sa.Column('collection_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('named_area_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['collection.id'], name='association_collection_id_fkey'),
    sa.ForeignKeyConstraint(['named_area_id'], ['named_area.id'], name='association_named_area_id_fkey')
    )
    # ### end Alembic commands ###
