"""Delete TaxonRelation rows whose parent_id or child_id is NULL.

Orphans appear because taxon_relation FKs are ON DELETE SET NULL: when a
taxon is deleted, its relation rows survive with a NULL endpoint and break
Taxon.get_children (which dereferences x.child).

Usage (inside docker/flask shell):
    python scripts/script-cleanup-orphan-taxon-relations.py --dry-run
    python scripts/script-cleanup-orphan-taxon-relations.py

Equivalent raw SQL:
    DELETE FROM taxon_relation WHERE child_id IS NULL OR parent_id IS NULL;
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_

from app.database import session
from app.models.taxon import TaxonRelation


def run(dry_run=False):
    q = session.query(TaxonRelation).filter(
        or_(TaxonRelation.parent_id.is_(None), TaxonRelation.child_id.is_(None))
    )
    rows = q.all()
    null_child = sum(1 for r in rows if r.child_id is None)
    null_parent = sum(1 for r in rows if r.parent_id is None)

    print(f'found {len(rows)} orphan rows '
          f'(null_child={null_child}, null_parent={null_parent})')
    for r in rows:
        print(f'  id={r.id} parent_id={r.parent_id} child_id={r.child_id} depth={r.depth}')

    if dry_run or not rows:
        return

    deleted = q.delete(synchronize_session=False)
    session.commit()
    print(f'deleted {deleted} rows')


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true',
                        help='List orphans without deleting.')
    args = parser.parse_args()

    from app.application import flask_app
    with flask_app.app_context():
        run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
