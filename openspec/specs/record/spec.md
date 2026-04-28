# Record Fields

A `Record` represents a collecting event (gathering). One record can have multiple `Unit`s (physical specimens).

---

## eventDate — Collecting Date

The date a specimen was collected. Stored in multiple columns to handle partial dates (year-only, year-month) from historical data.

| Column | Type | Notes |
|---|---|---|
| `collect_date` | DateTime | Full date; preferred when available |
| `collect_date_year` | Integer | Year component of a partial date |
| `collect_date_month` | Integer | Month component of a partial date |
| `collect_date_day` | Integer | Day component of a partial date |
| `verbatim_collect_date` | String | Raw string exactly as written on the label |

**Display priority** (first non-empty wins):
1. `collect_date` → formatted as `YYYY-MM-DD`
2. `{collect_date_year}-{collect_date_month}-{collect_date_day}` → formatted as available (year only, year-month, or full)
3. `verbatim_collect_date`

**Invariant**: `collect_date_year/month/day` were migrated from the removed `collect_date_text` column (migration `c5d3e6f7a8b9`, 2026-04-07). New records should use these columns directly; `collect_date_text` no longer exists.

---

## recordedBy — Collector

Who collected the specimen.

| Column | Type | Notes |
|---|---|---|
| `collector_id` | FK → Person | Structured; primary collector |
| `verbatim_collector` | String | Raw string as written on label (dwc:recordedBy) |
| `companion_text` | String | Unformatted companion collectors (HAST legacy) |
| `companion_text_en` | String | English version of companion text |

**Relationships**: `companions` → `RecordPerson` (ordered by sequence) for structured companion list.

**Display priority**:
1. `collector_id` → `Person.display_name`
2. `verbatim_collector`
3. Append `companion_text` / `companion_text_en` as supporting info

---

## locality — Collection Location

Where the specimen was collected.

| Column | Type | Notes |
|---|---|---|
| `locality_text` | String | Formatted locality description |
| `locality_text_en` | String | English version |
| `verbatim_locality` | String | Raw string as written on label |
| `altitude` | Integer | Minimum altitude (metres) |
| `altitude2` | Integer | Maximum altitude for a range (metres) |
| `latitude_decimal` | Numeric(9,6) | Decimal degrees |
| `longitude_decimal` | Numeric(9,6) | Decimal degrees |
| `verbatim_latitude` | String | Raw latitude as written |
| `verbatim_longitude` | String | Raw longitude as written |
| `geodetic_datum` | String | e.g. WGS84 |
| `coordinate_uncertainty_in_meters` | Numeric(10,2) | |

**Relationship**: `named_area_maps` → `RecordNamedAreaMap` → `NamedArea` (administrative areas: country, province, county, etc.)

---

## taxon — Identified Taxon

The taxonomic identification of the record. Determined by `Identification` records.

| Column | Type | Notes |
|---|---|---|
| `proxy_taxon_id` | FK → Taxon | Cache of latest identification's taxon |
| `proxy_taxon_scientific_name` | Text | Cache of scientific name |
| `proxy_taxon_common_name` | Text | Cache of common name |

**Source of truth**: The latest `Identification` (highest `sequence` value) determines the accepted identification. The `proxy_*` columns are denormalized cache to avoid joins on list views — update them when identification changes.

**Relationship**: `taxon_family` — resolved via `taxon_relation` closure table at depth=2 (genus→family), viewonly.

---

## Other Fields

| Column | Type | Notes |
|---|---|---|
| `field_number` | String | Collector's field number (indexed) |
| `field_number_int` | Integer | Parsed integer of field_number for sorting |
| `field_note` | Text | Field notes / remarks |
| `field_note_en` | Text | English version |
| `source_data` | JSONB | Raw import data; schema varies by source |
| `collection_id` | FK → Collection | Which collection this record belongs to |
| `project_id` | FK → Project | Optional project association |
| `event_id` | FK → Event | Optional collecting event grouping |
