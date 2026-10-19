"""Render the basdb greenhouse unit images (downloaded from s3://brmas-begonia)
as naturedb's size set, named for s3://brmas-hast/greenhouse/:

    {uuid}-{s|m|l|x|o}.jpg      (app.helpers_image.render_sizes: upright, THUMB_MAP)

uuid = uuid5(NAMESPACE, 'basdb-greenhouse-unitimage:{basdb image id}'): the same
name on every run and for every database, so the files can be uploaded once and
both dev and prod point at them (scripts/script-gen-greenhouse-images-rehost-sql.py).

Images are those greenhouse-unit-images.sql imports: an S3 object, a unit, and
not the same file again on the same unit (lowest basdb id kept). Already
rendered images (all sizes present) are skipped, so an interrupted run resumes.

Writes <export_dir>/greenhouse_unitimage-rehost.csv: basdb_image_id,uuid,aws_s3_path

usage (in the flask image, for Pillow):
    docker compose run --rm -v ~/d/basdb:/basdb flask \
        python scripts/script-render-greenhouse-images.py /basdb/export /basdb/images /basdb/greenhouse-upload \
        --owner "$(id -u):$(id -g)" [--limit N]
(importing app needs the container's root user: --owner hands the files back)
then upload:
    aws s3 sync ~/d/basdb/greenhouse-upload/ s3://brmas-hast/greenhouse/ --content-type image/jpeg
"""
import argparse
import csv
import os
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.helpers_image import THUMB_MAP, render_sizes  # noqa: E402

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'https://naturedb.org/basdb/greenhouse/unitimage')


def image_uuid(basdb_image_id):
    return str(uuid.uuid5(NAMESPACE, f'basdb-greenhouse-unitimage:{int(basdb_image_id)}'))


def images(export_dir):
    '''The basdb images greenhouse-unit-images.sql imports, in basdb id order.'''
    rows, seen = [], set()
    src = sorted(csv.DictReader(open(Path(export_dir) / 'greenhouse_unitimage.csv')), key=lambda r: int(r['id']))
    for r in src:
        if not r['unit_id'] or not r['s3_size'] or (r['unit_id'], r['aws_s3_path']) in seen:
            continue
        seen.add((r['unit_id'], r['aws_s3_path']))
        rows.append({'basdb_image_id': int(r['id']), 'uuid': image_uuid(r['id']), 'aws_s3_path': r['aws_s3_path']})
    return rows


def give(path, owner):
    if owner:
        os.chown(path, *owner)


def render(job):
    source, out_dir, name, owner = job
    targets = [Path(out_dir) / f'{name}-{code}.jpg' for code, _ in THUMB_MAP]
    if all(t.exists() for t in targets):
        return name, 'skipped', 0
    total = 0
    for (code, data), target in zip(render_sizes(source), targets):
        tmp = target.with_suffix('.part')
        tmp.write_bytes(data)
        give(tmp, owner)
        os.replace(tmp, target)  # no half-written file is ever taken as done
        total += len(data)
    return name, 'rendered', total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('export_dir')
    ap.add_argument('images_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--limit', type=int, help='only the first N images (trial run)')
    ap.add_argument('--workers', type=int, default=os.cpu_count())
    ap.add_argument('--owner', help='UID:GID to own the written files (the container runs as root)')
    args = ap.parse_args()
    owner = tuple(int(x) for x in args.owner.split(':')) if args.owner else None

    rows = images(args.export_dir)
    missing = [r for r in rows if not (Path(args.images_dir) / r['aws_s3_path']).exists()]
    if missing:
        sys.exit(f'{len(missing)} source files missing in {args.images_dir}, e.g. {missing[0]["aws_s3_path"]}')
    if args.limit:
        rows = rows[:args.limit]

    rehost_csv = Path(args.export_dir) / 'greenhouse_unitimage-rehost.csv'
    with open(rehost_csv, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, ['basdb_image_id', 'uuid', 'aws_s3_path'])
        w.writeheader()
        w.writerows(rows)
    give(rehost_csv, owner)

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    give(args.out_dir, owner)
    jobs = [(str(Path(args.images_dir) / r['aws_s3_path']), args.out_dir, r['uuid'], owner) for r in rows]
    counts, size = {'rendered': 0, 'skipped': 0}, 0
    with ProcessPoolExecutor(args.workers) as pool:
        for i, (name, status, n) in enumerate(pool.map(render, jobs, chunksize=4), 1):
            counts[status] += 1
            size += n
            if i % 200 == 0 or i == len(jobs):
                print(f'{i}/{len(jobs)} {counts} {size / 1e9:.2f} GB written', flush=True)


if __name__ == '__main__':
    main()
