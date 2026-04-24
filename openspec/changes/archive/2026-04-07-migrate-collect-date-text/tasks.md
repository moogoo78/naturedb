## 1. Alembic Migration

- [x] 1.1 Create new alembic migration that parses `collect_date_text` into `collect_date_year`, `collect_date_month`, `collect_date_day` using SQL regex, only for records where `collect_date IS NULL` and `collect_date_text IS NOT NULL`
- [x] 1.2 Handle pattern `YYYY-MM-DD` or `YYYY/MM/DD`: set year, month, day, and also set `collect_date`
- [x] 1.3 Handle pattern `YYYY-MM` or `YYYY/MM`: set year and month
- [x] 1.4 Handle pattern `YYYY`: set year only

## 2. Verification

- [x] 2.1 Query for remaining unparsed records (`collect_date_text IS NOT NULL AND collect_date_year IS NULL AND collect_date IS NULL`) and review count/values
