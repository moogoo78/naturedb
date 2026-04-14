## ADDED Requirements

### Requirement: Filter values are written to the URL querystring on search
The system SHALL update the browser URL querystring with all active filter values when a search is applied (via the search button or the advanced filter "apply" button). Empty/unset filters SHALL be omitted from the querystring. The URL SHALL be updated using `history.replaceState` without triggering a page reload.

#### Scenario: User applies filters via advanced search
- **WHEN** user sets family to "Orchidaceae" (id=42) and clicks the apply filter button
- **THEN** the browser URL updates to include `?family=42` and the search executes normally

#### Scenario: User searches via main search box
- **WHEN** user types "Quercus" in the main search box and clicks search
- **THEN** the browser URL updates to include `?q=Quercus`

#### Scenario: Multiple filters active
- **WHEN** user sets collection to "HAST" (id=1), family to id 42, and collector to id 78
- **THEN** the URL contains `?collection=1&family=42&collector=78`

#### Scenario: Empty filter values are excluded
- **WHEN** user leaves the genus field empty but sets family to id 42
- **THEN** the URL contains `?family=42` and does NOT contain a `genus` key

### Requirement: Filter form is restored from URL querystring on page load
The system SHALL read all recognized filter parameters from the URL querystring on page load and populate the corresponding form fields. For TomSelect comboboxes, the system SHALL fetch the required options from the API before setting the value. Cascading fields (family→genus→species, country→adm1→adm2→adm3) SHALL be restored in dependency order.

#### Scenario: Simple text field restored
- **WHEN** user navigates to `/data?accession_number=12345`
- **THEN** the accession_number input field is populated with "12345"

#### Scenario: TomSelect combobox restored
- **WHEN** user navigates to `/data?family=42`
- **THEN** the family TomSelect displays the family with id 42 (fetched from existing options) and the genus TomSelect is populated with genera under that family

#### Scenario: Cascading fields restored in order
- **WHEN** user navigates to `/data?family=42&genus=100&species=200`
- **THEN** family is set to 42, genus options are fetched and genus is set to 100, species options are fetched and species is set to 200

#### Scenario: Geographic cascade restored
- **WHEN** user navigates to `/data?country=5&adm1=10`
- **THEN** country is set to 5, adm1 options are fetched for country 5, and adm1 is set to 10

### Requirement: Search auto-triggers when URL has filter parameters
The system SHALL automatically execute a search on page load if the URL querystring contains any recognized filter parameters, after all form fields have been restored.

#### Scenario: Page load with filters triggers search
- **WHEN** user navigates to `/data?q=Quercus&collection=1`
- **THEN** the form fields are restored AND `applyFilter()` is called automatically, showing results

#### Scenario: Page load without filters shows empty state
- **WHEN** user navigates to `/data` with no querystring
- **THEN** no automatic search is triggered and the page shows its default empty state

### Requirement: Querystring is cleared when filters are reset
The system SHALL remove all filter-related querystring parameters from the URL when the user clicks the "clear" button on the filter form.

#### Scenario: User clears all filters
- **WHEN** user clicks the clear/reset button on the filter drawer
- **THEN** the browser URL is updated to `/data` (no querystring) via `history.replaceState`

### Requirement: All filter field types are supported
The system SHALL support syncing the following field types to/from the querystring:
- Text inputs: `accession_number`, `accession_number2`, `field_number`, `field_number2`, `altitude`, `altitude2`
- Date inputs: `collect_date`, `collect_date2`
- Native select: `collection`, `type_status`, `containent`, `altitude_condiction`
- TomSelect (with static options): `family`, `collect_month`
- TomSelect (with dynamic/cascading options): `genus`, `species`, `collector`, `country`, `adm1`, `adm2`, `adm3`
- Main search: `q`

#### Scenario: Date range filter round-trips through URL
- **WHEN** user sets collect_date to "2020-01-01" and collect_date2 to "2020-12-31" and applies the filter
- **THEN** URL contains `?collect_date=2020-01-01&collect_date2=2020-12-31`
- **AND WHEN** the page is reloaded
- **THEN** both date fields are restored with their original values

#### Scenario: Multi-value collect_month round-trips through URL
- **WHEN** user selects months 1, 6, 12 in collect_month and applies the filter
- **THEN** URL contains `collect_month=1,6,12` (comma-separated)
- **AND WHEN** the page is reloaded
- **THEN** collect_month TomSelect has all three months selected
