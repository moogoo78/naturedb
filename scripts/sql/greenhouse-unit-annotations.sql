-- Greenhouse room / propagation as unit annotations of collection 'greenhouse'.
-- basdb kept them as unit columns; the import parked them in
-- unit.source_data->'basdb'. naturedb stores per-collection custom fields as
-- annotation_type + unit_annotation, so the generic /api/v1/units filter and
-- facets cover them without greenhouse-specific code.
--
-- basdb category 'dead' is not copied: it is already unit.disposition.
-- prerequisites: scripts/sql/greenhouse-collection.sql, scripts/sql/greenhouse-units-ds2.sql
-- idempotent: annotation types are matched by (collection, name); units that
--             already have a value for a type are skipped.
-- run:  psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -f greenhouse-unit-annotations.sql

BEGIN;

CREATE TEMP TABLE _cfg ON COMMIT DROP AS
SELECT (SELECT id FROM collection WHERE name = 'greenhouse') AS collection_id;

DO $$ BEGIN
  IF (SELECT collection_id FROM _cfg) IS NULL THEN
    RAISE EXCEPTION 'collection greenhouse not found. Run scripts/sql/greenhouse-collection.sql first.';
  END IF;
END $$;

-- annotation_type.id lags behind rows inserted with explicit ids
SELECT setval(pg_get_serial_sequence('annotation_type', 'id'), GREATEST((SELECT max(id) FROM annotation_type), 1));

INSERT INTO annotation_type (name, label, target, input_type, sort, collection_id, data)
SELECT v.name, v.label, 'unit', 'select', v.sort, c.collection_id, v.data::jsonb
FROM _cfg c, (VALUES
  ('room', '房間', 1,
   '{"options": [["307", "307"], ["308", "308"], ["318", "318"], ["319", "319"], ["320", "320"], ["322", "322"], ["323", "323"], ["growing-box", "生長箱"]]}'),
  ('propagation', '類別', 2,
   '{"options": [["adult", "成株"], ["cutting", "葉插"], ["sowed", "播種"], ["seed-wild", "種子(野外)"], ["seed-give", "種子(贈送)"], ["legacy", "舊資料"]]}')
) AS v(name, label, sort, data)
WHERE NOT EXISTS (
  SELECT 1 FROM annotation_type t WHERE t.collection_id = c.collection_id AND t.name = v.name
);

INSERT INTO unit_annotation (unit_id, annotation_type_id, value, datetime)
SELECT u.id, t.id, u.source_data->'basdb'->>src.key, now() AT TIME ZONE 'Asia/Taipei'
FROM unit u
JOIN _cfg c ON u.collection_id = c.collection_id
CROSS JOIN (VALUES ('room', 'room'), ('propagation', 'category')) AS src(type_name, key)
JOIN annotation_type t ON t.collection_id = c.collection_id AND t.name = src.type_name
WHERE u.source_data ? 'basdb'
  AND COALESCE(u.source_data->'basdb'->>src.key, '') NOT IN ('', 'dead')
  AND NOT EXISTS (
    SELECT 1 FROM unit_annotation ua WHERE ua.unit_id = u.id AND ua.annotation_type_id = t.id
  );

SELECT t.name, ua.value, count(*)
FROM unit_annotation ua JOIN annotation_type t ON t.id = ua.annotation_type_id
WHERE t.collection_id = (SELECT collection_id FROM _cfg)
GROUP BY 1, 2 ORDER BY 1, 2;

COMMIT;
