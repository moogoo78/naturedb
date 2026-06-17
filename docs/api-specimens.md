# Specimens API

Public, read-only, cross-origin API for searching published specimens.

- **Endpoint:** `GET https://api.{domain}/v1/specimens`
- **Auth:** none. All data is public (`pub_status = 'P'`).
- **CORS:** open — `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, OPTIONS`, `Access-Control-Allow-Headers: Content-Type`.
- **No trailing slash.**

Served from the `api.{domain}` subdomain, so the path has no `/api` segment.
Internally the blueprint is registered at `/v1` (the reverse proxy routes
`api.{domain}` → the app). The legacy, host-scoped `{host}/api/v1/search`
endpoint remains for backward compatibility and returns the same per-row shape.

Source: `app/blueprints/public_api.py` (handler), `app/helpers_query.py`
(`make_specimen_query`, `serialize_specimen_row`).

---

## Query parameters

| Param    | Type                 | Default    | Description |
|----------|----------------------|------------|-------------|
| `q`      | string               | —          | Free-text search across catalog number, field number, collector name (zh/en) and proxy taxon scientific/common name. |
| `filter` | JSON object (string) | `{}`       | Structured filters. See [Filter keys](#filter-keys). URL-encode the JSON. |
| `sort`   | JSON array (string)  | `[]`       | List of sort keys. See [Sorting](#sorting). |
| `range`  | JSON array (string)  | `[0, 20]`  | `[start, end]` offset/limit window. See [Paging](#paging). |
| `site`   | string (slug)        | —          | Restrict to one site's collections. See [Site scope](#site-scope). |
| `total`  | any                  | —          | If present, its value is echoed back as `total` and the count query is skipped (faster paging). |

All of `filter`, `sort`, `range` are JSON encoded into the query string. A
free-text `q` given as a top-level param is folded into `filter.q`.

### Site scope

- **Omitted** → searches across **all** collections (cross-site).
- **Known slug** → restricts to that site's collections and applies its custom area classes.
- **Unknown slug** → `400 Bad Request` (a client typo, not an auth failure — all data is public).

### Filter keys

Passed inside the `filter` JSON object. Resolved by `make_specimen_query`.

| Key                  | Type            | Description |
|----------------------|-----------------|-------------|
| `q`                  | string          | Same free-text search as the top-level `q`. |
| `unit_id`            | int             | Exact unit id. |
| `taxon_id`           | int \| int[]    | Matches the taxon **and all its descendants**. |
| `taxon_name`         | string          | Substring match on proxy taxon scientific/common name. |
| `collector_id`       | int             | Exact collector (Person) id. |
| `field_number`       | string/int      | Exact field number; with `field_number2` becomes a numeric range. Legacy `"a--b"` syntax also accepted. |
| `field_number2`      | string/int      | Upper bound for a `field_number` range. |
| `collect_date`       | string          | `YYYY-MM-DD` exact; `"YYYY--YYYY"` or `"a--b"` range; `"YYYY-YYYY"` year range; or with `collect_date2`. |
| `collect_date2`      | string          | Upper bound for a `collect_date` range. |
| `collect_month`      | int             | Month (1–12). |
| `continent`          | string          | Continent name (e.g. `Asia`). |
| `country`            | int             | Named-area id for the country. Ignored if `named_area_id` is also set. |
| `named_area_id`      | int \| int[]    | One or more named-area ids (any-match for a list). |
| `locality_text`      | string          | Substring match on locality text. |
| `altitude`           | string          | Exact, or range `"min--max"` (partial `"min--"` / `"--max"` allowed). |
| `catalog_number`     | string          | Exact catalog number; with `catalog_number2` becomes a numeric range. |
| `catalog_number2`    | string          | Upper bound for a `catalog_number` numeric range. |
| `type_status`        | string          | Substring match on type status. |

> **Not supported here:** the `customFields` / `source_data` aggregation
> (`annotate`, `count`, JSONB field filters) available on the legacy
> `/api/v1/search` endpoint is **not** implemented by `/v1/specimens`. Do not
> rely on it through this endpoint.

### Sorting

`sort` is a JSON array. Prefix a key with `-` for descending. Default is
`-unit_id` (newest first).

| Key                | Meaning |
|--------------------|---------|
| `field_number`     | Collector sorting name, then numeric field number. |
| `collector`        | Same ordering as `field_number`. |
| `catalog_number`   | By catalog-number length then value (natural numeric order). |
| *any column name*  | Ordered by that column; `-name` for descending. |

### Paging

`range` is `[start, end]`.

- Returns rows `start` … `end` (offset `start`, limit `end - start`).
- The limit is **capped at 2000** rows per request.
- `[0, -1]` means **no limit** (use with care).

---

## Response

`200 OK`, `application/json`:

```json
{
  "data": [ /* array of specimen objects */ ],
  "total": 146386,
  "elapsed": 0.0123
}
```

| Field     | Type   | Description |
|-----------|--------|-------------|
| `data`    | array  | Specimen objects (see below). |
| `total`   | int    | Total matching specimens (the value of `total` param if supplied). |
| `elapsed` | float  | Query time in seconds. |

### Specimen object

Each element of `data` (from `serialize_specimen_row`):

| Field               | Type          | Description |
|---------------------|---------------|-------------|
| `unit_id`           | int           | Physical specimen (Unit) id. |
| `record_id`         | int           | Collection-event (Record) id. |
| `record_key`        | string        | `u{unit_id}`, or `c{record_id}` if no unit. |
| `catalog_number`    | string        | Catalog/accession number. |
| `image_url`         | string        | Cover image URL (may be empty). |
| `field_number`      | string        | Collector's field number. |
| `collector`         | object \| ""  | Collector (Person) dict, or `""` if none. |
| `collector_text`    | string        | Verbatim collector string. |
| `collect_date`      | string        | `YYYY-MM-DD`, or `""`. |
| `taxon`             | object        | Taxon dict, or `{}`. |
| `taxon_text`        | string        | `"Scientific name (common name)"`. |
| `named_areas`       | array         | Named-area dicts (administrative/geographic hierarchy). |
| `locality_text`     | string        | Free-text locality. |
| `altitude`          | number/string | Lower altitude bound. |
| `altitude2`         | number/string | Upper altitude bound. |
| `longitude_decimal` | number        | Decimal longitude. |
| `latitude_decimal`  | number        | Decimal latitude. |
| `type_status`       | string        | Type status, only when publicly published; otherwise `""`. |
| `link`              | string        | Public detail-page URL for the specimen. |

Only published specimens with a non-empty catalog number are returned.

---

## Errors

| Status | When |
|--------|------|
| `400`  | Unknown `site` slug. |
| `400`  | Malformed JSON in `filter` / `sort` / `range`. |

---

## Examples

Latest 3 specimens, any collection:

```bash
curl 'https://api.{domain}/v1/specimens?range=%5B0,3%5D'
```

Free-text search:

```bash
curl 'https://api.{domain}/v1/specimens?q=Quercus&range=%5B0,20%5D'
```

Filter by taxon (and descendants) within one site, sorted by catalog number:

```bash
curl 'https://api.{domain}/v1/specimens?site=hast&filter=%7B%22taxon_id%22%3A123%7D&sort=%5B%22catalog_number%22%5D'
```

The `filter` above is the URL-encoding of `{"taxon_id":123}`; `sort` is `["catalog_number"]`.

Get just the total count for a filter (the count is always in the envelope;
request a single row and read `total`):

```bash
curl 'https://api.{domain}/v1/specimens?q=Quercus&range=%5B0,1%5D'
# → {"data": [ ... 1 row ... ], "total": 1234, "elapsed": 0.01}
```
