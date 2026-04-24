## Why

We just added `collect_date_year`, `collect_date_month`, `collect_date_day` integer columns to the `record` table. The alembic migration populates these from `collect_date` (DateTime) where it exists, but records with only `collect_date_text` (partial dates stored as text like "1990" or "1992-03") are left unpopulated. We need to parse `collect_date_text` into the new columns so all partial date data is queryable.

## What Changes

- Add a data migration (alembic or standalone script) that parses `collect_date_text` values into `collect_date_year`, `collect_date_month`, `collect_date_day`
- Handle known text formats: "YYYY", "YYYY-MM", "YYYY-MM-DD", and slash variants
- Log unparseable values for manual review
- After migration, the new columns become the canonical source for partial dates; `collect_date_text` remains as legacy/fallback

## Capabilities

### New Capabilities
- `date-text-migration`: Parse existing `collect_date_text` values into the new integer year/month/day columns

### Modified Capabilities

(none)

## Impact

- **Database**: `record` table — updates `collect_date_year`, `collect_date_month`, `collect_date_day` for rows where `collect_date` is NULL but `collect_date_text` has a value
- **Data integrity**: Unparseable text values are preserved in `collect_date_text` as fallback
