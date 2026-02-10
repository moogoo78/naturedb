"""Batch upload images to S3, matching filenames to Unit.accession_number.

Usage:
    # inside docker container:
    cd /code && python script-upload-images.py --site hast --dir /path/to/images [--dry-run]

    # from host:
    docker compose exec flask bash -c "cd /code && python script-upload-images.py --site hast --dir /code/images"

Filename matching rules:
    Single unit:
        123456.jpg         -> accession_number='123456'
    Multi-unit (one image shared by multiple units):
        123456-123457.jpg  -> accession_number='123456' AND '123457'
        100-101-102.jpg    -> accession_number='100', '101', '102'
    Supported formats: .jpg, .jpeg, .png
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


class LocalFile:
    """Wraps a local file to match the interface expected by upload_image().

    upload_image() calls file_.filename and file_.read()
    """
    def __init__(self, path):
        self.path = Path(path)
        self.filename = self.path.name
        self._fh = None

    def read(self):
        return self.path.read_bytes()


import re

def parse_accession_numbers(filename):
    """Extract accession_number(s) from filename by pulling numeric sequences.

    Returns a list of accession numbers.

    Rules:
        - Strip extension
        - Strip trailing " (1)", " (2)" (download duplicates)
        - Find all numeric sequences of 3+ digits (ignore short suffixes like -1)
        - Each sequence is an accession number

    Examples:
        '123456.jpg'                    -> ['123456']
        '0100617-0100618.jpg'           -> ['0100617', '0100618']
        'ASIZF0100617.jpg'              -> ['0100617']
        'ASIZF0100617-ASIZF0100618.jpg' -> ['0100617', '0100618']
        'ASIZF 0100089-1.JPG'           -> ['0100089']
        'ASIZF 0100089 (1).JPG'         -> ['0100089']
    """
    stem = Path(filename).stem.strip()

    # Strip trailing download duplicate suffix like " (1)", " (2)"
    stem = re.sub(r'\s*\(\d+\)$', '', stem).strip()

    # Extract all numeric sequences with 3+ digits
    numbers = re.findall(r'\d{3,}', stem)

    return numbers if numbers else []


def main():
    parser = argparse.ArgumentParser(description='Batch upload images matched by accession_number')
    parser.add_argument('--site', required=True, help='Site name (e.g. hast)')
    parser.add_argument('--dir', required=True, help='Directory containing image files')
    parser.add_argument('--collection-id', type=int, default=None, help='Filter units by collection_id')
    parser.add_argument('--dry-run', action='store_true', help='Show matches without uploading')
    parser.add_argument('--skip-existing', action='store_true', default=True, help='Skip units that already have a cover image (default: True)')
    args = parser.parse_args()

    image_dir = Path(args.dir)
    if not image_dir.is_dir():
        print(f'ERROR: {args.dir} is not a directory')
        sys.exit(1)

    # Collect image files
    extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
    image_files = [f for f in image_dir.iterdir() if f.suffix.lower() in extensions]

    if not image_files:
        print(f'No image files found in {args.dir}')
        sys.exit(0)

    print(f'Found {len(image_files)} image files')

    # Build file_path -> [accession_numbers] map
    # and accession_number -> file_path reverse map
    file_acc_map = {}   # file_path -> [acc1, acc2, ...]
    acc_file_map = {}   # acc -> file_path

    for f in image_files:
        accs = parse_accession_numbers(f.name)
        if accs:
            file_acc_map[f] = accs
            for acc in accs:
                acc_file_map[acc] = f
        else:
            print(f'  SKIP: cannot parse accession_number from {f.name}')

    all_accession_numbers = list(acc_file_map.keys())

    print(f'Parsed {len(all_accession_numbers)} accession numbers from {len(file_acc_map)} files')

    multi_files = {f: accs for f, accs in file_acc_map.items() if len(accs) > 1}
    if multi_files:
        print(f'  ({len(multi_files)} multi-unit files)')

    # Flask app context required for DB access and upload_image
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.database import session
        from app.models.site import Site
        from app.models.collection import Unit, MultimediaObject
        from app.helpers_image import upload_image

        site = Site.query.filter(Site.name == args.site).first()
        if not site:
            print(f'ERROR: site "{args.site}" not found')
            sys.exit(1)

        upload_conf = site.get_settings('admin.uploads')
        if not upload_conf:
            print(f'ERROR: admin.uploads not configured for site "{args.site}"')
            sys.exit(1)

        serv_keys = site.get_service_keys()

        # Query all matching units
        query = Unit.query.filter(Unit.accession_number.in_(all_accession_numbers))
        if args.collection_id:
            query = query.filter(Unit.collection_id == args.collection_id)
        else:
            collection_ids = site.collection_ids
            query = query.filter(Unit.collection_id.in_(collection_ids))

        units = query.all()
        unit_map = {}  # acc -> unit
        for u in units:
            unit_map[u.accession_number] = u

        print(f'Matched {len(unit_map)} units in database\n')

        # Report unmatched accession numbers
        matched_acc = set(unit_map.keys())
        unmatched_acc = set(all_accession_numbers) - matched_acc
        if unmatched_acc:
            print(f'Unmatched accession numbers ({len(unmatched_acc)}):')
            for acc in sorted(unmatched_acc)[:20]:
                print(f'  {acc_file_map[acc].name} (accession: {acc})')
            if len(unmatched_acc) > 20:
                print(f'  ... and {len(unmatched_acc) - 20} more')
            print()

        # Upload: iterate by file, not by unit
        uploaded = 0
        units_linked = 0
        skipped = 0
        failed = 0

        for image_path, accession_numbers in sorted(file_acc_map.items(), key=lambda x: x[0].name):
            # Find matched units for this file
            matched_units = []
            for acc in accession_numbers:
                if acc in unit_map:
                    matched_units.append((acc, unit_map[acc]))

            if not matched_units:
                continue

            # Check if all matched units already have covers
            if args.skip_existing:
                units_needing_image = [(acc, u) for acc, u in matched_units if not u.cover_image_id]
                if not units_needing_image:
                    accs_str = ', '.join(acc for acc, _ in matched_units)
                    print(f'  SKIP (all have cover): {image_path.name} -> [{accs_str}]')
                    skipped += len(matched_units)
                    continue
                matched_units = units_needing_image

            accs_str = ', '.join(acc for acc, _ in matched_units)
            unit_ids_str = ', '.join(str(u.id) for _, u in matched_units)

            if args.dry_run:
                print(f'  DRY-RUN: {image_path.name} -> units [{unit_ids_str}] ({accs_str})')
                uploaded += 1
                units_linked += len(matched_units)
                continue

            try:
                # Upload once, using first unit's ID as the S3 key prefix
                first_unit = matched_units[0][1]
                local_file = LocalFile(image_path)
                res = upload_image(upload_conf, serv_keys, local_file, f'u{first_unit.id}')

                if res['error'] == '' and res['message'] == 'ok':
                    sd = {'originalFilename': image_path.name}
                    exif = res.get('exif', {})
                    if exif:
                        sd['exifData'] = exif

                    # Parse photo taken date from EXIF
                    date_created = None
                    for exif_key in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                        if raw_date := exif.get(exif_key):
                            try:
                                date_created = datetime.strptime(raw_date, '%Y:%m:%d %H:%M:%S')
                                break
                            except (ValueError, TypeError):
                                continue

                    # Create a MultimediaObject per unit, same file_url
                    for acc, unit in matched_units:
                        mo = MultimediaObject(
                            type_id=1,
                            physical_format_id=1,
                            context_id=1,
                            unit_id=unit.id,
                            source_data=sd,
                            file_url=res['file_url'],
                            date_created=date_created,
                        )
                        session.add(mo)
                        session.commit()

                        unit.cover_image_id = mo.id
                        session.commit()

                    print(f'  OK: {image_path.name} -> units [{unit_ids_str}] ({accs_str})')
                    uploaded += 1
                    units_linked += len(matched_units)
                else:
                    print(f'  FAIL: {image_path.name} -> {res["error"]}')
                    failed += 1

            except Exception as e:
                print(f'  ERROR: {image_path.name} -> {e}')
                failed += 1

        print(f'\nDone. files_uploaded={uploaded} units_linked={units_linked} skipped={skipped} failed={failed}')


if __name__ == '__main__':
    main()
