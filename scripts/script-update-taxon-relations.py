"""Set higher-taxon relations from CSV / stdin.

CSV columns (header required): taxon_id, genus_id, family_id
  - taxon_id: required. The taxon to update.
  - genus_id: optional. Empty value clears the genus parent.
  - family_id: optional. Empty value clears the family parent.

Extra columns are ignored. Rank-invalid parents are skipped silently by
Taxon.make_relations (e.g. a family-rank taxon ignores a family_id column).

Usage (inside docker/flask shell):
    python scripts/script-update-taxon-relations.py --input relations.csv
    python scripts/script-update-taxon-relations.py --input relations.csv --dry-run
    python scripts/script-update-taxon-relations.py < relations.csv
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import session
from app.models.taxon import Taxon


def _parse_id(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return int(value)


def run(reader, dry_run=False):
    updated = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        try:
            taxon_id = _parse_id(row.get('taxon_id'))
        except ValueError:
            errors.append(f'row {row_num}: invalid taxon_id {row.get("taxon_id")!r}')
            continue
        if not taxon_id:
            errors.append(f'row {row_num}: missing taxon_id')
            continue

        taxon = session.get(Taxon, taxon_id)
        if not taxon:
            errors.append(f'row {row_num}: taxon {taxon_id} not found')
            continue

        try:
            rel_data = {
                'family': _parse_id(row.get('family_id')),
                'genus': _parse_id(row.get('genus_id')),
            }
        except ValueError as e:
            errors.append(f'row {row_num}: invalid parent id ({e})')
            continue

        prefix = '[dry-run] ' if dry_run else ''
        print(f'{prefix}taxon {taxon_id} rank={taxon.rank} <- {rel_data}')
        if dry_run:
            continue

        try:
            taxon.make_relations(rel_data)
        except Exception as e:
            session.rollback()
            errors.append(f'row {row_num}: taxon {taxon_id} failed: {e}')
            continue
        updated += 1

    print(f'\n{updated} updated', file=sys.stderr)
    if errors:
        print(f'{len(errors)} errors:', file=sys.stderr)
        for e in errors:
            print(f'  {e}', file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', help='CSV file path. Reads stdin if omitted.')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing.')
    args = parser.parse_args()

    stream = open(args.input, newline='') if args.input else sys.stdin
    try:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or 'taxon_id' not in reader.fieldnames:
            sys.exit(f'CSV must contain a "taxon_id" column (found: {reader.fieldnames})')

        from app.application import flask_app
        with flask_app.app_context():
            run(reader, dry_run=args.dry_run)
    finally:
        if args.input:
            stream.close()


if __name__ == '__main__':
    main()
