"""Generate SQL that imports the basdb greenhouse units skipped by
script-gen-greenhouse-units-sql.py (<basdb_export_dir>/greenhouse_unit-ds2-uncovered.csv)
into collection 'greenhouse'.

Record per unit, by basdb skip reason:
  multiple        existing record: lowest candidate id (the candidates are
                  duplicate records of one gathering: same collector/number/date)
  no_contact MM-  existing record with that field number and collect date
                  (Myanmar expedition records, collector NULL in naturedb)
  no collection   new empty record per unit (the admin form needs a record);
                  source_data->'basdb'->>'unit_id' = basdb unit id
  anything else   new record per basdb greenhouse_collection, as in
                  script-gen-greenhouse-import-sql.py, except that an unmatched
                  collector is kept as verbatim_collector; the placeholder
                  contact TEMP (and blank contacts) get no collector and TEMP no
                  field number, since its numbers are basdb's temporary sequence
Skipped: test rows (collect_num 'test').

New records go to record_group 'greenhouse'; units carry the full basdb unit row in
unit.source_data -> 'basdb', like greenhouse-units-ds2.sql. Run
scripts/sql/greenhouse-unit-annotations.sql afterwards to backfill room/propagation.

Prerequisites on the target DB: everything greenhouse-units-ds2.sql needs, and that file.

usage:
    python3 scripts/script-gen-greenhouse-uncovered-sql.py <basdb_export_dir> \
        > scripts/sql/greenhouse-units-uncovered.sql
"""
import csv
import importlib.util
import json
import re
import sys
from pathlib import Path


def _load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f'{name}.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


units_gen = _load('script-gen-greenhouse-units-sql')  # unit fields, as in greenhouse-units-ds2.sql
records_gen = _load('script-gen-greenhouse-import-sql')  # record fields, as in greenhouse-no-record-import.sql
q = units_gen.q

PLACEHOLDER_CONTACTS = {'TEMP'}
SN = re.compile(r'^s\.?\s*n\.?$', re.I)


def taxon_names(export_dir):
    '''basdb taxon id -> naturedb full name in tree 1 (same rules as the no-record import)'''
    out = {}
    for r in csv.DictReader(open(f'{export_dir}/taxon-basdb-naturedb-mapping.csv')):
        if r['naturedb_name']:
            out[r['basdb_taxon_id']] = r['naturedb_name']
        elif r['match_method'] == 'none':
            out[r['basdb_taxon_id']] = ' '.join(r['basdb_name'].split())
        elif r['naturedb_accepted_name']:
            out[r['basdb_taxon_id']] = r['naturedb_accepted_name']
    return out


def collector(contact_id, contacts):
    '''(collector_by, collector_key, verbatim_collector)'''
    c = contacts.get(contact_id, {})
    name = (c.get('basdb_name') or '').strip()
    method = c.get('match_method')
    if method == 'manual':
        return 'basdb_contact_id', contact_id, name
    if method == 'pid' or c.get('naturedb_pid'):
        return 'pid', c['naturedb_pid'], name
    if method in ('name', 'human') and c.get('naturedb_person_id'):
        return 'id', c['naturedb_person_id'], name
    if not name or name in PLACEHOLDER_CONTACTS:
        return 'none', None, None
    return 'verbatim', None, name


def main(export_dir):
    uncovered = list(csv.DictReader(open(f'{export_dir}/greenhouse_unit-ds2-uncovered.csv')))
    units = {r['id']: r for r in csv.DictReader(open(f'{export_dir}/greenhouse_unit.csv'))}
    gc = {r['id']: r for r in csv.DictReader(open(f'{export_dir}/greenhouse_collection.csv'))}
    tags = {r['id']: r for r in csv.DictReader(open(f'{export_dir}/greenhouse_trackingtag.csv'))}
    tx = {r['id']: r for r in csv.DictReader(open(f'{export_dir}/taxon_scientificname.csv'))}
    contacts = {r['basdb_id']: r for r in csv.DictReader(open(f'{export_dir}/record_contact-naturedb-mapping-edited.csv'))}
    tnames = taxon_names(export_dir)

    records, unit_rows, skipped = {}, [], []
    for x in uncovered:
        u = units[x['unit_id']]
        g = gc.get(x['gc_id'], {})
        num = (g.get('collect_num') or '').strip()

        if num == 'test':
            skipped.append(x['unit_id'])
            continue

        if x['reason'] == 'multiple':
            link = ('record_id', str(min(int(i) for i in x['candidate_record_ids'].split('|'))), num, None)
        elif x['reason'] == 'no_contact' and num.startswith('MM-'):
            link = ('field_number', num, num, g['collect_date'] or None)
        elif not g:
            link = ('basdb_unit_id', u['id'], None, None)
            records[f'unit:{u["id"]}'] = (
                None, None, 'none', None, None, None, None, None, None,
                json.dumps({'basdb': {'unit_id': int(u['id']), 'note': 'greenhouse unit without collection'}}),
            )
        else:
            link = ('basdb_id', g['id'], None, None)
            by, key, verbatim_collector = collector(g['contact_id'], contacts)
            contact_name = (contacts.get(g['contact_id'], {}).get('basdb_name') or '').strip()
            if contact_name in PLACEHOLDER_CONTACTS or not num:
                field_number = None
            elif SN.match(num):
                field_number = 's.n.'
            else:
                field_number = num
            rbge = tx.get(g['taxon_id'] or '', {}).get('name', '')
            ident = g['verbatim_scientific_name'].strip()
            ident = rbge if ident in ('', 'nan') else ident
            records[f'gc:{g["id"]}'] = (
                int(g['id']), field_number, by, key, verbatim_collector, g['collect_date'] or None,
                g['locality'].strip() or None, ident or None, tnames.get(g['taxon_id'] or ''),
                json.dumps({'basdb': records_gen.basdb_fields(g)}, ensure_ascii=False),
            )

        tag = tags.get(u['tracking_tag_id'] or '')
        is_dead = u['is_dead'] == 't' or u['category'] == 'dead'
        notes = list(dict.fromkeys(m.strip() for m in (u['memo'], u['memo2']) if m.strip()))
        unit_rows.append((
            int(u['id']), *link,
            tag['qrcode_sn'] if tag else None,
            units_gen.KIND.get(u['category'], 'whole organism'),
            units_gen.DEAD if is_dead else 'in collection',
            units_gen.PUB_STATUS,
            '\n'.join(notes) or None,
            u['created'] or None,
            json.dumps({'basdb': units_gen.basdb_fields(u, tag)}, ensure_ascii=False),
        ))

    w = sys.stdout.write
    w(f'''-- Import the basdb greenhouse units skipped by greenhouse-units-ds2.sql
-- generated by scripts/script-gen-greenhouse-uncovered-sql.py from basdb export
-- source: greenhouse_unit-ds2-uncovered.csv: {len(unit_rows)} units, {len(records)} new records,
--         {len(skipped)} skipped (test rows: basdb unit {', '.join(skipped) or '-'})
--
-- prerequisites: scripts/sql/greenhouse-units-ds2.sql (and its prerequisites)
-- afterwards:    scripts/sql/greenhouse-unit-annotations.sql (room / propagation backfill)
-- idempotent: records by basdb collection / unit id, units by basdb unit id
-- run:  psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -f greenhouse-units-uncovered.sql

BEGIN;

CREATE TEMP TABLE _cfg ON COMMIT DROP AS
SELECT (SELECT id FROM collection WHERE name = 'greenhouse') AS collection_id,
       (SELECT id FROM record_group WHERE name = 'greenhouse' AND collection_id = 1) AS group_id;

DO $$ BEGIN
  IF (SELECT collection_id FROM _cfg) IS NULL OR (SELECT group_id FROM _cfg) IS NULL THEN
    RAISE EXCEPTION 'collection / record_group greenhouse not found. Run the earlier greenhouse imports first.';
  END IF;
END $$;

-- new records ---------------------------------------------------------------
CREATE TEMP TABLE _rsrc (
  rec_key text, gc_id int, field_number text, collector_by text, collector_key text,
  verbatim_collector text, collect_date date, verbatim_locality text,
  verbatim_identification text, taxon_name text, source_data jsonb
) ON COMMIT DROP;

INSERT INTO _rsrc VALUES
''')
    w(',\n'.join(
        f'  ({q(k)}, {q(gid)}, {q(fn)}, {q(by)}, {q(key)}, {q(vc)}, {q(cd)}, {q(loc)}, {q(vi)}, {q(tn)}, {q(sd)}::jsonb)'
        for k, (gid, fn, by, key, vc, cd, loc, vi, tn, sd) in records.items()) + ';\n')
    w(r'''
CREATE TEMP TABLE _taxon ON COMMIT DROP AS
SELECT DISTINCT ON (n) n AS name, id, full_scientific_name, common_name
FROM (SELECT regexp_replace(trim(full_scientific_name), '\s+', ' ', 'g') AS n, id, full_scientific_name, common_name
      FROM taxon WHERE tree_id = 1) t
ORDER BY n, id;

CREATE TEMP TABLE _rres ON COMMIT DROP AS
SELECT s.*,
  CASE s.collector_by
    WHEN 'basdb_contact_id' THEN (SELECT min(p.id) FROM person p WHERE p.source_data->>'basdb_contact_id' = s.collector_key)
    WHEN 'pid'              THEN (SELECT min(p.id) FROM person p WHERE p.source_data->>'pid' = s.collector_key)
    WHEN 'id'               THEN (SELECT p.id FROM person p WHERE p.id = s.collector_key::int)
  END AS collector_id,
  t.id AS taxon_id, t.full_scientific_name AS taxon_full_name, t.common_name AS taxon_common_name
FROM _rsrc s
LEFT JOIN _taxon t ON t.name = s.taxon_name;

DO $$
DECLARE n int; missing text;
BEGIN
  SELECT count(*), string_agg(DISTINCT collector_by || ':' || collector_key, ', ')
    INTO n, missing FROM _rres WHERE collector_by IN ('basdb_contact_id', 'pid', 'id') AND collector_id IS NULL;
  IF n > 0 THEN
    RAISE EXCEPTION '% rows have no naturedb collector: %. Run basdb create-person-from-basdb.sql first.', n, missing;
  END IF;
  SELECT count(*) INTO n FROM _rres WHERE taxon_name IS NOT NULL AND taxon_id IS NULL;
  IF n > 0 THEN
    RAISE EXCEPTION '% rows name a taxon missing from tree 1. Run scripts/sql/begonia-new-taxa.sql first.', n;
  END IF;
END $$;

-- records of an earlier run, by basdb collection id or (no collection) basdb unit id
CREATE TEMP TABLE _rexisting ON COMMIT DROP AS
SELECT CASE WHEN source_data->'basdb'->>'id' IS NOT NULL THEN 'gc:' || (source_data->'basdb'->>'id')
            ELSE 'unit:' || (source_data->'basdb'->>'unit_id') END AS rec_key,
       min(id) AS record_id
FROM record
WHERE collection_id = 1 AND (source_data->'basdb'->>'id' IS NOT NULL OR source_data->'basdb'->>'unit_id' IS NOT NULL)
GROUP BY 1;

CREATE TEMP TABLE _rnew (rec_key text, record_id int) ON COMMIT DROP;

WITH ins AS (
  INSERT INTO record (
    created, updated, collection_id, collector_id, verbatim_collector,
    field_number, field_number_int,
    collect_date, collect_date_year, collect_date_month, collect_date_day, verbatim_collect_date,
    verbatim_locality,
    proxy_taxon_id, proxy_taxon_scientific_name, proxy_taxon_common_name,
    source_data
  )
  SELECT now() AT TIME ZONE 'Asia/Taipei', now() AT TIME ZONE 'Asia/Taipei', 1, r.collector_id,
    CASE WHEN r.collector_id IS NULL THEN r.verbatim_collector END,
    r.field_number, substring(r.field_number from '\d+')::int,
    r.collect_date, extract(year from r.collect_date)::int, extract(month from r.collect_date)::int,
    extract(day from r.collect_date)::int, r.source_data->'basdb'->>'collect_date',
    r.verbatim_locality,
    r.taxon_id, COALESCE(r.taxon_full_name, r.verbatim_identification), r.taxon_common_name,
    r.source_data
  FROM _rres r
  WHERE NOT EXISTS (SELECT 1 FROM _rexisting e WHERE e.rec_key = r.rec_key)
  ORDER BY r.rec_key
  RETURNING id, source_data
)
INSERT INTO _rnew
SELECT CASE WHEN source_data->'basdb'->>'id' IS NOT NULL THEN 'gc:' || (source_data->'basdb'->>'id')
            ELSE 'unit:' || (source_data->'basdb'->>'unit_id') END, id
FROM ins;

INSERT INTO identification (created, updated, record_id, taxon_id, verbatim_identification, sequence)
SELECT now() AT TIME ZONE 'Asia/Taipei', now() AT TIME ZONE 'Asia/Taipei', n.record_id, r.taxon_id,
       r.verbatim_identification, 0
FROM _rnew n JOIN _rres r ON r.rec_key = n.rec_key
WHERE r.taxon_id IS NOT NULL OR r.verbatim_identification IS NOT NULL;

INSERT INTO record_group_map (record_id, group_id, created, updated)
SELECT n.record_id, (SELECT group_id FROM _cfg), now() AT TIME ZONE 'Asia/Taipei', now() AT TIME ZONE 'Asia/Taipei'
FROM _rnew n;

-- units ---------------------------------------------------------------------
CREATE TEMP TABLE _usrc (
  basdb_unit_id int, link_by text, link_key text, field_number text, collect_date date,
  catalog_number text, kind_of_unit text, disposition text, pub_status text, notes text,
  created timestamp, source_data jsonb
) ON COMMIT DROP;

INSERT INTO _usrc VALUES
''')
    w(',\n'.join(
        f'  ({uid}, {q(by)}, {q(key)}, {q(fn)}, {q(cd)}, {q(cat)}, {q(kind)}, {q(disp)}, {q(pub)}, {q(notes)}, '
        f'{q(created)}::timestamptz AT TIME ZONE \'Asia/Taipei\', {q(sd)}::jsonb)'
        for uid, by, key, fn, cd, cat, kind, disp, pub, notes, created, sd in unit_rows) + ';\n')
    w(r'''
CREATE TEMP TABLE _ures ON COMMIT DROP AS
SELECT s.*,
  CASE s.link_by
    WHEN 'record_id'     THEN (SELECT r.id FROM record r WHERE r.id = s.link_key::int AND r.collection_id = 1
                                 AND r.field_number IS NOT DISTINCT FROM s.field_number)
    WHEN 'field_number'  THEN (SELECT min(r.id) FROM record r WHERE r.collection_id = 1 AND r.field_number = s.link_key
                                 AND r.collect_date::date IS NOT DISTINCT FROM s.collect_date
                                 HAVING count(*) = 1)
    WHEN 'basdb_id'      THEN (SELECT x.record_id FROM (SELECT * FROM _rexisting UNION ALL SELECT * FROM _rnew) x
                                 WHERE x.rec_key = 'gc:' || s.link_key)
    WHEN 'basdb_unit_id' THEN (SELECT x.record_id FROM (SELECT * FROM _rexisting UNION ALL SELECT * FROM _rnew) x
                                 WHERE x.rec_key = 'unit:' || s.link_key)
  END AS record_id
FROM _usrc s;

DO $$
DECLARE n int; bad text;
BEGIN
  SELECT count(*), string_agg(link_by || ':' || link_key, ', ') INTO n, bad FROM _ures WHERE record_id IS NULL;
  IF n > 0 THEN
    RAISE EXCEPTION '% units have no record (%): mapping is stale for this DB.', n, bad;
  END IF;
END $$;

CREATE TEMP TABLE _uexisting ON COMMIT DROP AS
SELECT (source_data->'basdb'->>'id')::int AS basdb_unit_id
FROM unit WHERE collection_id = (SELECT collection_id FROM _cfg) AND source_data->'basdb' IS NOT NULL;

INSERT INTO unit (
  created, updated, record_id, collection_id, basis_of_record, kind_of_unit,
  catalog_number, disposition, pub_status, notes, source_data
)
SELECT COALESCE(r.created, now() AT TIME ZONE 'Asia/Taipei'), now() AT TIME ZONE 'Asia/Taipei',
  r.record_id, (SELECT collection_id FROM _cfg), 'LivingSpecimen', r.kind_of_unit,
  r.catalog_number, r.disposition, r.pub_status, r.notes, r.source_data
FROM _ures r
WHERE NOT EXISTS (SELECT 1 FROM _uexisting e WHERE e.basdb_unit_id = r.basdb_unit_id)
ORDER BY r.basdb_unit_id;

DO $$
DECLARE n_rec int; n_unit int; n_skip int; n_verbatim int; n_total int;
BEGIN
  SELECT count(*) INTO n_rec FROM _rnew;
  SELECT count(*) INTO n_skip FROM _uexisting e JOIN _usrc s ON s.basdb_unit_id = e.basdb_unit_id;
  SELECT count(*) - n_skip INTO n_unit FROM _usrc;
  SELECT count(*) INTO n_verbatim FROM record r JOIN _rnew n ON n.record_id = r.id WHERE r.verbatim_collector IS NOT NULL;
  SELECT count(*) INTO n_total FROM unit WHERE collection_id = (SELECT collection_id FROM _cfg);
  RAISE NOTICE 'records inserted: % (verbatim collector: %), units inserted: %, already imported: %, greenhouse units total: %',
    n_rec, n_verbatim, n_unit, n_skip, n_total;
END $$;

COMMIT;
''')
    print(f'{len(unit_rows)} units, {len(records)} new records, skipped {skipped}', file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1])
