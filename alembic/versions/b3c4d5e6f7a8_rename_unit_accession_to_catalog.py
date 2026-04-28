"""rename unit.accession_number to catalog_number, duplication_number to extended_catalog_number

Revision ID: b3c4d5e6f7a8
Revises: e8f9a0b1c2d3
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op


revision = 'b3c4d5e6f7a8'
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('unit', 'accession_number', new_column_name='catalog_number')
    op.alter_column('unit', 'duplication_number', new_column_name='extended_catalog_number')
    op.execute('ALTER INDEX ix_unit_accession_number RENAME TO ix_unit_catalog_number')
    op.execute("UPDATE annotation_type SET name = 'catalog_number_issue' WHERE name = 'accession_number_issue'")


def downgrade():
    op.execute("UPDATE annotation_type SET name = 'accession_number_issue' WHERE name = 'catalog_number_issue'")
    op.execute('ALTER INDEX ix_unit_catalog_number RENAME TO ix_unit_accession_number')
    op.alter_column('unit', 'extended_catalog_number', new_column_name='duplication_number')
    op.alter_column('unit', 'catalog_number', new_column_name='accession_number')
