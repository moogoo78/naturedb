## MODIFIED Requirements

### Requirement: Mock specimen dataset
The Explorer view SHALL load specimen data from the JSON API endpoints `/api/v1/scribe/collections` and `/api/v1/scribe/specimens` (paginated). It SHALL NOT load `app/static/js/annotate/specimens.mock.json` for the grid in v2 (the file MAY remain in the tree until the Annotation detail view is also wired). The Explorer SHALL issue an authenticated-or-anonymous read of these endpoints; v2 of this spec defers authentication.

#### Scenario: Initial load fetches collections then specimens
- **WHEN** the page first paints on a scribe host
- **THEN** the client SHALL issue `GET /api/v1/scribe/collections` once
- **AND** the client SHALL issue `GET /api/v1/scribe/specimens?page=1&per_page=50` to populate the grid
- **AND** the client SHALL NOT fetch `specimens.mock.json` for the Explorer grid

#### Scenario: Pagination
- **WHEN** the visitor clicks "Next" in the pagination control while on page 1 of N (N > 1)
- **THEN** the client SHALL issue `GET /api/v1/scribe/specimens?…&page=2`
- **AND** the grid SHALL re-render with the page-2 items
- **AND** the pagination indicator SHALL read "Page 2 of N"

#### Scenario: Server-side search
- **WHEN** the visitor types a query into the search box
- **THEN** after a debounce window the client SHALL issue `GET /api/v1/scribe/specimens?…&q=<query>&page=1`
- **AND** the grid SHALL re-render with the server-filtered page-1 items

#### Scenario: Server-side sort
- **WHEN** the visitor selects a sort option
- **THEN** the client SHALL issue `GET /api/v1/scribe/specimens?…&sort=<key>&page=1` and re-render

## ADDED Requirements

### Requirement: Institution+Collection facet
The Explorer rail SHALL include an **Institution / Collection** facet group at the top of the rail, populated from `GET /api/v1/scribe/collections`. Each row SHALL render a display label (e.g. `HAST:vascular`, `PPI`) and a unit count. Selecting a row SHALL set the active `collection_id` filter and re-fetch the specimens page; selecting it again (or clicking an "All" affordance) SHALL clear the filter.

#### Scenario: Facet rows ordered by count
- **WHEN** the rail renders the Institution / Collection group
- **THEN** the rows SHALL be ordered by unit count descending
- **AND** rows whose `collection.id` is not present in `Config.SCRIBE_COLLECTION_LABELS` SHALL NOT appear

#### Scenario: Selecting a collection filters the grid
- **WHEN** the visitor clicks the row for `HAST:vascular`
- **THEN** the client SHALL issue `GET /api/v1/scribe/specimens?collection_id=1&page=1&per_page=50`
- **AND** the grid SHALL show only units in collection 1

#### Scenario: Bare org-code label for default-named collections
- **WHEN** a `collection.id` maps in `Config.SCRIBE_COLLECTION_LABELS` to a string with no `:` separator (e.g. `'PPI'`)
- **THEN** the facet row SHALL render that string verbatim, with no sub-collection badge

### Requirement: Stub fields on specimen cards
The shaped specimen rows returned by `/api/v1/scribe/specimens` SHALL include the fields `status`, `completeness`, `pending`, `medium`, and `color` derived from real columns:
- `status` SHALL be `'verified'` when `unit.pub_status='P'`, otherwise `'in-review'`.
- `completeness` SHALL be the integer percentage (0-100) of populated key fields out of: `proxy_taxon_scientific_name`, `proxy_taxon_common_name`, `taxon_family`, `verbatim_collector`/`collector`, `collect_date`, `locality_text`, `unit.catalog_number`.
- `pending` SHALL be `0` until v3 wires real pending-annotation counts.
- `medium` SHALL be derived from kingdom via a fixed map (Plantae→`leaf`, Animalia→`insect`, Mineralia→`mineral`, Fungi→`mushroom`); unknown kingdom falls back to `'specimen'`.
- `color` SHALL be derived from the same kingdom map.

#### Scenario: Public unit reports verified
- **WHEN** a unit's `pub_status='P'` is shaped
- **THEN** its `status` SHALL be `'verified'`

#### Scenario: Hidden unit reports in-review
- **WHEN** a unit's `pub_status='H'` is shaped
- **THEN** its `status` SHALL be `'in-review'`

#### Scenario: Completeness over a fully-populated row
- **WHEN** all 7 key fields are populated for a record
- **THEN** the shaped `completeness` SHALL be `100`

### Requirement: Inert legacy facets
The rail facet groups Kingdom, Family, Region, Date collected, Annotation status, Completeness, and Handwritten label SHALL remain rendered in the DOM but SHALL NOT mutate the active filter set when their controls are interacted with. Selecting a checkbox in any of these groups SHALL not trigger a `/specimens` refetch.

#### Scenario: Kingdom checkbox is inert
- **WHEN** the visitor checks "Plantae" in the Kingdom facet
- **THEN** the client SHALL NOT issue any new `/api/v1/scribe/specimens` request
- **AND** the displayed grid SHALL NOT change

### Requirement: Pagination response shape
The `/api/v1/scribe/specimens` endpoint SHALL respond with a JSON object containing `items` (array of shaped specimen rows), `page` (1-indexed integer), `per_page` (integer), and `total` (integer count of all matching rows ignoring pagination). `per_page` SHALL be clamped to the inclusive range [1, 100].

#### Scenario: Default pagination
- **WHEN** a request omits `page` and `per_page`
- **THEN** the response SHALL set `page=1` and `per_page=50`

#### Scenario: per_page clamp
- **WHEN** a request specifies `per_page=500`
- **THEN** the server SHALL clamp the value to `100` and return `per_page=100` in the response
