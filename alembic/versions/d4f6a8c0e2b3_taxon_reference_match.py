"""taxon_reference_match: stored local -> reference-tree (TaiCOL) taxon match

Revision ID: d4f6a8c0e2b3
Revises: c3e5a7b9d1f2
Create Date: 2026-11-11 12:00:00.000000

Filled by scripts/script-build-taxon-reference-match.py; read by the
specimen page and the TBIA feed (Taxon.get_reference_matches).
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f6a8c0e2b3'
down_revision = 'c3e5a7b9d1f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'taxon_reference_match',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('taxon_id', sa.Integer, sa.ForeignKey('taxon.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tree_id', sa.Integer, sa.ForeignKey('taxon_tree.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ref_taxon_id', sa.Integer, sa.ForeignKey('taxon.id', ondelete='SET NULL')),
        sa.Column('match_type', sa.String(20), nullable=False),
        sa.Column('is_manual', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('matched_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('note', sa.Text),
        sa.UniqueConstraint('taxon_id', 'tree_id', name='uq_taxon_reference_match_taxon_tree'),
    )
    op.create_index('ix_taxon_reference_match_ref_taxon_id', 'taxon_reference_match', ['ref_taxon_id'])


def downgrade():
    op.drop_index('ix_taxon_reference_match_ref_taxon_id', 'taxon_reference_match')
    op.drop_table('taxon_reference_match')
