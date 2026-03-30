# Data Validator

A CLI tool to detect and tag data quality issues within a collection.

## Checks

### Date range (`record.collect_date`, `identification.date`)

Valid range: `1700-01-01` to today.

Detected issues:
- **before 1700** — date is before 1700-01-01
- **future date** — date is after today

> Impossible calendar dates (e.g. Feb 30) are not checked because PostgreSQL's `DateTime` type rejects them at write time.

### Duplicate accession number (`unit.accession_number`)

Detects units within the same collection that share the same `accession_number` value. Empty and NULL values are excluded.

---

## CLI Usage

```sh
# Report issues to stdout
flask validate <collection_id>

# Export issues to CSV
flask validate <collection_id> -o issues.csv

# Write issues as annotations in DB
flask validate <collection_id> --tag

# Clear previous validator annotations then re-tag
flask validate <collection_id> --tag --clear

# Tag and export at once
flask validate <collection_id> --tag --clear -o issues.csv
```

---

## CSV Output

Columns: `check`, `type`, `record_id`, `id`, `field`, `value`, `reason`, `unit_ids`, `count`

| check | type | record_id | id | field | value | reason | unit_ids | count |
|---|---|---|---|---|---|---|---|---|
| date | record | 134966 | | collect_date | 1631-12-31 | before 1700 | | |
| date | identification | 91860 | 442 | date | 7986-02-12 | future date | | |
| accession_number | unit | | | accession_number | HAST12345 | duplicate | 101;205 | 2 |

---

## Annotations

When `--tag` is used, issues are stored in the database as annotations (not assertions — see below).

### AnnotationType auto-created on first run

| name | label | target |
|---|---|---|
| `date_issue` | 日期問題 | record |
| `accession_number_issue` | 館號重複 | unit |

These are created automatically per collection on the first `--tag` run. They can also be created manually via Admin > 標本標註.

### Annotation value format

- Date issue: `collect_date: 1631-12-31 (before 1700)`
- Accession number issue: `HAST12345`

### Clearing annotations

`--clear` deletes all `RecordAnnotation` / `UnitAnnotation` rows written by the validator (matched by `annotation_type.name` in `date_issue`, `accession_number_issue`) before writing new ones. Use this when re-running after data corrections.

---

## Annotation vs. Assertion

| | Assertion (`RecordAssertion` / `UnitAssertion`) | Annotation (`RecordAnnotation` / `UnitAnnotation`) |
|---|---|---|
| Purpose | Scientific data (habitat, phenology, etc.) | Data management / QC |
| Published to DwC | Yes (via `assertionOccurrenceMap`) | No |
| Admin section | 標註類別 | 標本標註 |
| Written by validator | No | Yes |

---

## Admin Record List Filter

When annotation types with `target='record'` exist for the site's collections, a **資料問題** dropdown appears in the record list filter bar. Selecting a type filters records to only those that have a matching `RecordAnnotation`.

The dropdown is hidden automatically on sites that have no record-level annotation types — no configuration needed.

### How it works

1. `record_list()` queries `AnnotationType` where `target='record'` and `collection_id` is in the site's collections, passing results to the template as `annotation_types`
2. The template renders the dropdown only if `annotation_types` is non-empty
3. On submit, `annotation_type_id` is included in the filter payload sent to `/admin/api/records`
4. `make_items_stmt()` joins `record_annotation` and filters by `annotation_type_id`

---

## Code

| Path | Description |
|---|---|
| `app/validator.py` | `validate_dates()`, `validate_accession_numbers()`, `tag_issues()`, `clear_tags()` |
| `app/commands.py` | `flask validate` CLI command |
| `app/models/collection.py` | `RecordAnnotation` model, `AnnotationType.TARGET_OPTIONS` |
| `app/blueprints/admin.py` | `record_list()` passes `annotation_types` to template |
| `app/helpers_query.py` | `make_items_stmt()` joins `RecordAnnotation` on `annotation_type_id` filter |
| `app/templates/admin/record-list.html` | 資料問題 filter dropdown |
| `alembic/versions/a3f1c2d4e5b6_record_annotation.py` | Migration for `record_annotation` table |
