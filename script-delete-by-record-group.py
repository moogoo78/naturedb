"""
Delete all records (and their units) that belong to a given record_group.

Membership is defined solely by the `record_group_map` association table
(group_id -> record_id). The RecordGroup row itself is NOT deleted.

Why this is not a plain `session.delete(record)`:
  - `Record.units` has no ORM cascade and `unit.record_id` is ON DELETE
    SET NULL, so deleting a record ORPHANS its units instead of removing
    them. Units must be deleted explicitly.
  - Several child tables reference record/unit with ON DELETE NO ACTION
    (record_annotation, record_group_map, record_named_area_map,
    annotation, unit_annotation). Those block a bare DELETE, so their
    rows are cleared first. All other children are CASCADE / SET NULL and
    are handled by Postgres automatically.

The blocking child tables are discovered dynamically from pg_constraint so
the script keeps working if the schema gains new foreign keys.

Safe by default: runs as a DRY RUN unless --commit is passed. All deletes
run inside a single transaction; any error rolls the whole thing back.

Run inside the flask container:
  # preview only
  docker compose exec flask bash -c "cd /code && python script-delete-by-record-group.py <group_id>"
  # actually delete
  docker compose exec flask bash -c "cd /code && python script-delete-by-record-group.py <group_id> --commit"
"""

import argparse

from sqlalchemy import text

from app.database import session
from app.models.collection import RecordGroup

CHUNK = 5000  # max ids per DELETE ... WHERE id IN (...) to bound query size


def chunked(seq, size=CHUNK):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def discover_blocking_children(parent_table):
    """Return [(child_table, child_col)] for FKs to parent_table whose
    ON DELETE rule is NO ACTION ('a') or RESTRICT ('r') -- i.e. the ones
    that would block a DELETE and must be cleared manually."""
    sql = text("""
        SELECT c.conrelid::regclass::text AS child, a.attname AS child_col
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
          AND c.confrelid::regclass::text = :parent
          AND c.confdeltype IN ('a', 'r')
        ORDER BY child
    """)
    return [(r.child, r.child_col) for r in session.execute(sql, {'parent': parent_table})]


def count_children(children, id_col, ids):
    """Count child rows that reference the given parent ids, per table."""
    counts = {}
    for table, col in children:
        total = 0
        for chunk in chunked(ids):
            n = session.execute(
                text(f"SELECT count(*) FROM {table} WHERE {col} IN :ids"),
                {'ids': tuple(chunk)},
            ).scalar()
            total += n
        counts[f'{table}.{col}'] = total
    return counts


def delete_by_ids(table, col, ids):
    deleted = 0
    for chunk in chunked(ids):
        res = session.execute(
            text(f"DELETE FROM {table} WHERE {col} IN :ids"),
            {'ids': tuple(chunk)},
        )
        deleted += res.rowcount or 0
    return deleted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('group_id', type=int, help='record_group.id to purge')
    parser.add_argument('--commit', action='store_true',
                        help='actually delete (default is a dry-run preview)')
    args = parser.parse_args()

    group = session.get(RecordGroup, args.group_id)
    if not group:
        print(f"ERROR: record_group id={args.group_id} not found")
        return
    print(f"record_group id={group.id} name={group.name!r} "
          f"category={group.category!r} collection_id={group.collection_id}")

    # Capture target ids up front (before any delete invalidates the lookup).
    record_ids = [r[0] for r in session.execute(
        text("SELECT record_id FROM record_group_map WHERE group_id = :gid"),
        {'gid': group.id},
    )]
    if not record_ids:
        print("No records in this group. Nothing to do.")
        return

    unit_ids = [r[0] for r in session.execute(
        text("SELECT id FROM unit WHERE record_id IN :ids"),
        {'ids': tuple(record_ids)},
    )] if record_ids else []

    unit_children = discover_blocking_children('unit')
    record_children = discover_blocking_children('record')

    print(f"\nTargets: {len(record_ids)} record(s), {len(unit_ids)} unit(s)")
    print("Blocking child rows to clear first:")
    if unit_ids:
        for k, v in count_children(unit_children, 'unit_id', unit_ids).items():
            print(f"  {k:34} {v}")
    for k, v in count_children(record_children, 'record_id', record_ids).items():
        print(f"  {k:34} {v}")
    print("(other child tables are ON DELETE CASCADE / SET NULL -- handled by Postgres)")

    if not args.commit:
        print("\nDRY RUN -- nothing deleted. Re-run with --commit to apply.")
        return

    try:
        # 1) units first: clear blocking unit children, then the units
        for table, col in unit_children:
            n = delete_by_ids(table, col, unit_ids)
            if n:
                print(f"deleted {n} from {table}")
        nu = delete_by_ids('unit', 'id', unit_ids)
        print(f"deleted {nu} unit(s)")

        # 2) records: clear blocking record children, then the records
        for table, col in record_children:
            n = delete_by_ids(table, col, record_ids)
            if n:
                print(f"deleted {n} from {table}")
        nr = delete_by_ids('record', 'id', record_ids)
        print(f"deleted {nr} record(s)")

        session.commit()
        print("\nCommitted. RecordGroup row left intact.")
    except Exception as exc:
        session.rollback()
        print(f"\nERROR -- rolled back, nothing deleted: {exc}")
        raise


if __name__ == '__main__':
    main()
