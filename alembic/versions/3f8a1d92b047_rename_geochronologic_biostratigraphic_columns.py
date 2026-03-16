"""rename geochronologic and biostratigraphic columns in record_geological_context

Revision ID: 3f8a1d92b047
Revises: 5cc2cedf7d7f
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f8a1d92b047'
down_revision = '5cc2cedf7d7f'
branch_labels = None
depends_on = None


def upgrade():
    # Renames
    op.alter_column('record_geological_context', 'earliest_geochronologic',
                    new_column_name='geochronologic_text')
    op.alter_column('record_geological_context', 'latest_geochronologic',
                    new_column_name='geochronologic_text2')
    op.alter_column('record_geological_context', 'earliest_geochronologic_prefix',
                    new_column_name='geochronologic_option')
    op.alter_column('record_geological_context', 'latest_geochronologic_prefix',
                    new_column_name='geochronologic_prefix2')
    op.alter_column('record_geological_context', 'lowest_biostratigraphic_zone',
                    new_column_name='biostratigraphic_zone')
    op.alter_column('record_geological_context', 'highest_biostratigraphic_zone',
                    new_column_name='biostratigraphic_zone2')
    # New columns
    op.add_column('record_geological_context',
                  sa.Column('geochronologic_text_en', sa.String(length=500), nullable=True))
    op.add_column('record_geological_context',
                  sa.Column('geochronologic_option_prefix', sa.String(length=50), nullable=True))


def downgrade():
    # Drop new columns
    op.drop_column('record_geological_context', 'geochronologic_option_prefix')
    op.drop_column('record_geological_context', 'geochronologic_text_en')
    # Reverse renames
    op.alter_column('record_geological_context', 'geochronologic_text',
                    new_column_name='earliest_geochronologic')
    op.alter_column('record_geological_context', 'geochronologic_text2',
                    new_column_name='latest_geochronologic')
    op.alter_column('record_geological_context', 'geochronologic_option',
                    new_column_name='earliest_geochronologic_prefix')
    op.alter_column('record_geological_context', 'geochronologic_prefix2',
                    new_column_name='latest_geochronologic_prefix')
    op.alter_column('record_geological_context', 'biostratigraphic_zone',
                    new_column_name='lowest_biostratigraphic_zone')
    op.alter_column('record_geological_context', 'biostratigraphic_zone2',
                    new_column_name='highest_biostratigraphic_zone')
