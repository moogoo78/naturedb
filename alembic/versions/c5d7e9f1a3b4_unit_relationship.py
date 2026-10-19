"""unit_relationship replaces unit.parent_id and propagation

Revision ID: c5d7e9f1a3b4
Revises: b4c6d8e0f2a3
Create Date: 2026-10-17 10:00:00.000000

Relations between units follow Darwin Core ResourceRelationship: unit_id is
relationship_of_resource of related_unit_id, with a date, remarks and
according_to. It replaces
- unit.parent_id: one untyped parent per unit (親代標本); each becomes a
  "derived from" row
- propagation: dated events on one unit (type, date, note), copied from
  basdb's greenhouse model; each becomes a "propagation" row without a
  related unit, type and note in remarks. Rows whose unit was deleted
  (unit_id NULL) have nothing to attach to and are dropped.
created/updated are naturedb local time (UTC+8, app.utils.get_time).
"""
from alembic import op


revision = 'c5d7e9f1a3b4'
down_revision = 'b4c6d8e0f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('''
        CREATE TABLE unit_relationship (
            id SERIAL PRIMARY KEY,
            unit_id INTEGER NOT NULL REFERENCES unit(id) ON DELETE CASCADE,
            related_unit_id INTEGER REFERENCES unit(id) ON DELETE SET NULL,
            relationship_of_resource VARCHAR(100) NOT NULL,
            established_date DATE,
            according_to VARCHAR(500),
            remarks TEXT,
            created TIMESTAMP WITHOUT TIME ZONE,
            updated TIMESTAMP WITHOUT TIME ZONE,
            CONSTRAINT ck_unit_relationship_not_self CHECK (related_unit_id IS NULL OR related_unit_id <> unit_id)
        )
    ''')
    op.execute('CREATE INDEX ix_unit_relationship_unit_id ON unit_relationship (unit_id)')
    op.execute('CREATE INDEX ix_unit_relationship_related_unit_id ON unit_relationship (related_unit_id)')

    op.execute('''
        INSERT INTO unit_relationship (unit_id, related_unit_id, relationship_of_resource, created, updated)
        SELECT id, parent_id, 'derived from', now() AT TIME ZONE 'Asia/Taipei', now() AT TIME ZONE 'Asia/Taipei'
        FROM unit
        WHERE parent_id IS NOT NULL AND parent_id <> id
        ORDER BY id
    ''')
    op.execute('''
        INSERT INTO unit_relationship (unit_id, relationship_of_resource, established_date, remarks, created, updated)
        SELECT unit_id, 'propagation', date,
               NULLIF(concat_ws(': ', NULLIF(propagation_type, ''), NULLIF(note, '')), ''),
               coalesce(created, now() AT TIME ZONE 'Asia/Taipei'), coalesce(updated, now() AT TIME ZONE 'Asia/Taipei')
        FROM propagation
        WHERE unit_id IS NOT NULL
        ORDER BY id
    ''')

    op.execute('ALTER TABLE unit DROP COLUMN parent_id')
    op.execute('DROP TABLE propagation')


def downgrade():
    op.execute('SET lock_timeout = \'5s\'')
    op.execute('ALTER TABLE unit ADD COLUMN parent_id INTEGER REFERENCES unit(id) ON DELETE SET NULL')
    op.execute('''
        CREATE TABLE propagation (
            id SERIAL PRIMARY KEY,
            propagation_type VARCHAR(50),
            unit_id INTEGER REFERENCES unit(id) ON DELETE SET NULL,
            date DATE,
            note VARCHAR(1000),
            created TIMESTAMP WITHOUT TIME ZONE,
            updated TIMESTAMP WITHOUT TIME ZONE
        )
    ''')
    # a unit had one parent: keep the first "derived from" per unit
    op.execute('''
        UPDATE unit SET parent_id = r.related_unit_id
        FROM (
            SELECT DISTINCT ON (unit_id) unit_id, related_unit_id
            FROM unit_relationship
            WHERE relationship_of_resource = 'derived from' AND related_unit_id IS NOT NULL
            ORDER BY unit_id, id
        ) r
        WHERE unit.id = r.unit_id
    ''')
    # remarks were "type: note"; the split is not recoverable, keep it in note
    op.execute('''
        INSERT INTO propagation (unit_id, date, note, created, updated)
        SELECT unit_id, established_date, remarks, created, updated
        FROM unit_relationship
        WHERE relationship_of_resource = 'propagation'
        ORDER BY id
    ''')
    op.execute('DROP TABLE unit_relationship')
