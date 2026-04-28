## Context

The `record` table has a `collect_date_text` column (String) that stores partial dates as free text (e.g. "1990", "1992-03") when a complete date couldn't be parsed into the `collect_date` DateTime column. We recently added `collect_date_year`, `collect_date_month`, `collect_date_day` integer columns and populated them from `collect_date` via alembic migration. Records with only `collect_date_text` still have NULL year/month/day columns.

## Goals / Non-Goals

**Goals:**
- Parse `collect_date_text` into `collect_date_year`, `collect_date_month`, `collect_date_day` for all records where `collect_date` is NULL
- Log unparseable values so they can be reviewed manually

**Non-Goals:**
- Dropping the `collect_date_text` column (keep as legacy fallback)
- Fixing records with bad `collect_date` values (e.g. future dates) — that's a separate data quality task
- Handling exotic date formats (e.g. "Spring 1990", "late March") — these stay in `collect_date_text`

## Decisions

**Alembic migration vs standalone script**: Use an alembic migration with raw SQL. This ensures the migration runs exactly once as part of the normal deploy pipeline and is tracked by alembic's version history. A standalone script risks being run multiple times or forgotten.

**Parsing approach**: Use SQL pattern matching (regex) directly in the migration rather than loading rows into Python. This is faster for bulk updates and avoids ORM overhead. Handle these patterns:
1. `YYYY` — year only (4 digits)
2. `YYYY-MM` or `YYYY/MM` — year and month
3. `YYYY-MM-DD` or `YYYY/MM/DD` — full date (also set `collect_date`)

**Unparseable values**: Leave `collect_date_text` intact; the display logic already falls back to it. No separate logging needed since a simple query (`WHERE collect_date_text IS NOT NULL AND collect_date_year IS NULL`) can find them after migration.

## Risks / Trade-offs

- **Ambiguous formats**: Text like "03-1990" (month-year) or "1990.03" won't match standard patterns → left unparsed, discoverable via query. Low risk since the admin form generates "YYYY", "YYYY-MM" formats.
- **Data overwrite**: Migration only touches rows where `collect_date` is NULL, so already-populated year/month/day values from the previous migration are safe.
