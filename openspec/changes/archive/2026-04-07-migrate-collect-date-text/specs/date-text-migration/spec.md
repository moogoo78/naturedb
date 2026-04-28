## ADDED Requirements

### Requirement: Parse year-only text dates
The migration SHALL extract the year from `collect_date_text` values matching the pattern `YYYY` (4 digits) and set `collect_date_year` accordingly, leaving `collect_date_month` and `collect_date_day` as NULL.

#### Scenario: Year-only value
- **WHEN** a record has `collect_date` IS NULL and `collect_date_text = '1990'`
- **THEN** `collect_date_year` SHALL be set to 1990, `collect_date_month` and `collect_date_day` SHALL remain NULL

### Requirement: Parse year-month text dates
The migration SHALL extract year and month from `collect_date_text` values matching `YYYY-MM` or `YYYY/MM` and set `collect_date_year` and `collect_date_month` accordingly.

#### Scenario: Year-month with dash
- **WHEN** a record has `collect_date` IS NULL and `collect_date_text = '1992-03'`
- **THEN** `collect_date_year` SHALL be 1992, `collect_date_month` SHALL be 3, `collect_date_day` SHALL remain NULL

#### Scenario: Year-month with slash
- **WHEN** a record has `collect_date` IS NULL and `collect_date_text = '1992/03'`
- **THEN** `collect_date_year` SHALL be 1992, `collect_date_month` SHALL be 3, `collect_date_day` SHALL remain NULL

### Requirement: Parse full date text dates
The migration SHALL extract year, month, and day from `collect_date_text` values matching `YYYY-MM-DD` or `YYYY/MM/DD`, set all three columns, and also set `collect_date` to the corresponding DateTime.

#### Scenario: Full date in text
- **WHEN** a record has `collect_date` IS NULL and `collect_date_text = '1992-03-15'`
- **THEN** `collect_date_year` SHALL be 1992, `collect_date_month` SHALL be 3, `collect_date_day` SHALL be 15, and `collect_date` SHALL be set to `1992-03-15`

### Requirement: Preserve unparseable values
The migration SHALL NOT modify `collect_date_text`. Records with text that does not match any supported pattern SHALL be left unchanged (year/month/day remain NULL).

#### Scenario: Unrecognized format
- **WHEN** a record has `collect_date_text = 'Spring 1990'`
- **THEN** `collect_date_year`, `collect_date_month`, `collect_date_day` SHALL remain NULL, and `collect_date_text` SHALL remain `'Spring 1990'`

### Requirement: Skip already-populated records
The migration SHALL only process records where `collect_date` IS NULL, to avoid overwriting values populated from the DateTime column.

#### Scenario: Record with existing collect_date
- **WHEN** a record has `collect_date = '2024-03-15'` and `collect_date_text = '2024-03'`
- **THEN** the migration SHALL NOT modify `collect_date_year`, `collect_date_month`, or `collect_date_day` for this record
