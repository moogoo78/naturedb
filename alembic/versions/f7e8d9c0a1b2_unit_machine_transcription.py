"""unit_machine_transcription: raw AI/OCR base layer + unit_verbatim override linkage

Revision ID: f7e8d9c0a1b2
Revises: c7d4e8a1b2f3
Create Date: 2026-07-06 00:00:00.000000

Adds an immutable, write-once base layer for machine (AI/OCR) transcriptions and
wires `unit_verbatim` up as a sparse human-override layer:
  - unit_machine_transcription: one row per extraction run; full structured output
    lives in `result` (JSONB), with a derived `min_confidence` promoted to a real
    column for review-queue filtering.
  - unit_verbatim gains:
      * machine_transcription_id -> which run a human row corrects (reference, not copy)
      * parent_id                -> self-referential lineage of the correction chain
      * is_active                -> the accepted version per (unit_id, section_type),
                                    enforced by a partial unique index.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'f7e8d9c0a1b2'
down_revision = 'c7d4e8a1b2f3'
branch_labels = None
depends_on = None


def upgrade():
    # --- base layer: immutable machine (AI/OCR) transcription runs -----------
    op.create_table(
        'unit_machine_transcription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        # 'ai' | 'ocr'
        sa.Column('engine', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=50), nullable=True),
        # full structured output, keyed by section_type:
        #   {"locality": {"text": "...", "confidence": 0.81}, ...}
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        # derived worst-field score, promoted out of `result` for indexed review queues
        sa.Column('min_confidence', sa.Numeric(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(), nullable=True),
        # write-once; no `updated` column on purpose — this table is never mutated
        sa.Column('created', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['unit_id'], ['unit.id'],
            name=op.f('fk_unit_machine_transcription_unit_id_unit'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_unit_machine_transcription')),
    )
    op.create_index(
        op.f('ix_unit_machine_transcription_unit_id'),
        'unit_machine_transcription', ['unit_id'], unique=False,
    )
    # review-queue filter: "units with a low-confidence field"
    op.create_index(
        op.f('ix_unit_machine_transcription_min_confidence'),
        'unit_machine_transcription', ['min_confidence'], unique=False,
    )
    # prompt_version A/B comparison, scoped per unit
    op.create_index(
        op.f('ix_unit_machine_transcription_prompt_version'),
        'unit_machine_transcription', ['unit_id', 'prompt_version'], unique=False,
    )

    # --- override layer: unit_verbatim as a sparse human-correction layer -----
    op.add_column(
        'unit_verbatim',
        sa.Column('machine_transcription_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'unit_verbatim',
        sa.Column('parent_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'unit_verbatim',
        sa.Column(
            'is_active', sa.Boolean(),
            server_default=sa.text('false'), nullable=False,
        ),
    )

    op.create_foreign_key(
        op.f('fk_unit_verbatim_machine_transcription_id_unit_machine_transcription'),
        'unit_verbatim', 'unit_machine_transcription',
        ['machine_transcription_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_unit_verbatim_parent_id_unit_verbatim'),
        'unit_verbatim', 'unit_verbatim',
        ['parent_id'], ['id'],
        ondelete='SET NULL',
    )

    op.create_index(
        op.f('ix_unit_verbatim_machine_transcription_id'),
        'unit_verbatim', ['machine_transcription_id'], unique=False,
    )
    op.create_index(
        op.f('ix_unit_verbatim_parent_id'),
        'unit_verbatim', ['parent_id'], unique=False,
    )
    # exactly one accepted version per (unit_id, section_type)
    op.create_index(
        'uq_unit_verbatim_active',
        'unit_verbatim', ['unit_id', 'section_type'],
        unique=True,
        postgresql_where=sa.text('is_active'),
    )


def downgrade():
    op.drop_index('uq_unit_verbatim_active', table_name='unit_verbatim')
    op.drop_index(op.f('ix_unit_verbatim_parent_id'), table_name='unit_verbatim')
    op.drop_index(
        op.f('ix_unit_verbatim_machine_transcription_id'),
        table_name='unit_verbatim',
    )
    op.drop_constraint(
        op.f('fk_unit_verbatim_parent_id_unit_verbatim'),
        'unit_verbatim', type_='foreignkey',
    )
    op.drop_constraint(
        op.f('fk_unit_verbatim_machine_transcription_id_unit_machine_transcription'),
        'unit_verbatim', type_='foreignkey',
    )
    op.drop_column('unit_verbatim', 'is_active')
    op.drop_column('unit_verbatim', 'parent_id')
    op.drop_column('unit_verbatim', 'machine_transcription_id')

    op.drop_index(
        op.f('ix_unit_machine_transcription_prompt_version'),
        table_name='unit_machine_transcription',
    )
    op.drop_index(
        op.f('ix_unit_machine_transcription_min_confidence'),
        table_name='unit_machine_transcription',
    )
    op.drop_index(
        op.f('ix_unit_machine_transcription_unit_id'),
        table_name='unit_machine_transcription',
    )
    op.drop_table('unit_machine_transcription')
