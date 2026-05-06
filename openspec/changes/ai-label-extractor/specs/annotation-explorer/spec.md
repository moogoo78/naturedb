## ADDED Requirements

### Requirement: Specimen payload includes AI extraction summary
The `GET /api/v1/scribe/specimens` response SHALL include an `ai_extraction` field per specimen item carrying the latest persisted extraction at the active prompt version, or `null` if none exists. This field SHALL be populated by `shape_specimens_page` via a single batched query, not per-row lookups.

#### Scenario: Card list response shape
- **WHEN** the explorer fetches a page of specimens
- **THEN** each item in `items[]` SHALL include `ai_extraction: { text, model, backend, ms, created_at } | null`

#### Scenario: Single batched query
- **WHEN** a page of N specimens is shaped
- **THEN** the shaper SHALL issue exactly one additional `SELECT` against `unit_ai_extraction` filtered by `unit_id IN (...)` and `prompt_version = <active>`

### Requirement: Transcription modal AI panel mount point
The modal layout SHALL provide a stable mount point inside the `image-rail` for the AI panel. The existing two rail sections ("Specimen plate", "Recent annotators") SHALL keep their order, with the AI section inserted between them when `FEATURE_AI_LABEL` is enabled.

#### Scenario: Section order with feature on
- **WHEN** the modal opens and the AI feature flag is on
- **THEN** the rail SHALL render the sections in order: "Specimen plate" → "AI label reader" → "Recent annotators"

#### Scenario: Section order with feature off
- **WHEN** the AI feature flag is off
- **THEN** the rail SHALL render only the original two sections in their original order
