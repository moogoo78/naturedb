## ADDED Requirements

### Requirement: Annotation explorer route
The application SHALL expose a public route `/annotate` that renders the Explorer view as the default screen. The route SHALL be served by the existing `frontpage` blueprint and SHALL NOT require authentication in v1.

#### Scenario: Anonymous visitor opens the explorer
- **WHEN** an unauthenticated visitor requests `GET /annotate`
- **THEN** the server SHALL return HTTP 200 with the Explorer view rendered

#### Scenario: Direct link to a specimen
- **WHEN** a visitor opens `/annotate#<catalog>` where `<catalog>` matches a specimen's `id` in the mock dataset
- **THEN** the page SHALL load with the Annotation view active for that specimen
- **AND** the back/forward browser buttons SHALL toggle between Explorer and Annotation views without a server round-trip

#### Scenario: Unknown specimen in hash
- **WHEN** a visitor opens `/annotate#<catalog>` for a catalog not present in the mock dataset
- **THEN** the page SHALL fall back to the Explorer view and the hash SHALL be cleared

### Requirement: Mock specimen dataset
The page SHALL render against a static JSON dataset shipped at `app/static/js/annotate/specimens.mock.json` containing the 12 specimens and 4-key facet structure ported from `nature-scribe/project/data.jsx`. The page SHALL NOT issue any database queries or authenticated API calls in v1.

#### Scenario: Dataset shape
- **WHEN** the JS module loads `specimens.mock.json`
- **THEN** the response SHALL be a JSON object with two top-level keys, `specimens` (array) and `facets` (object with `kingdom`, `family`, `region`, `status` keys)
- **AND** each specimen SHALL include the fields `id`, `catalog`, `kingdom`, `taxon`, `common`, `family`, `collector`, `collected`, `locality`, `completeness`, `annotations`, `pending`, `status`, `medium`, `color`

#### Scenario: No DB access
- **WHEN** the `/annotate` request is served
- **THEN** the request handler SHALL NOT call `session.execute`, `session.query`, or any model class

### Requirement: Explorer faceted filters
The Explorer view SHALL provide a left rail with collapsible facet groups for Kingdom, Family, Region, Date collected (year range), Annotation status, Completeness, and Handwritten label. Filters SHALL apply client-side without a page reload, and active filters SHALL be reflected as removable chips in the result bar.

#### Scenario: Multi-select kingdom filter
- **WHEN** the visitor checks two kingdom checkboxes (e.g. `Plantae` and `Animalia`)
- **THEN** the result grid SHALL show only specimens whose `kingdom` matches one of the checked values
- **AND** the result count SHALL update to the filtered count
- **AND** the active-chips bar SHALL display one chip per checked kingdom with a `×` close affordance

#### Scenario: Clear all filters
- **WHEN** any filter is active and the visitor clicks "Clear (N)" in the rail head
- **THEN** all facet selections, the completeness range, and the search box SHALL reset to their defaults
- **AND** the full unfiltered specimen grid SHALL be displayed

#### Scenario: Completeness range quick-set
- **WHEN** the visitor clicks "Low (< 50%)" in the Completeness facet
- **THEN** the completeness range SHALL be set to `[0, 50]`
- **AND** only specimens with `completeness` in that range SHALL be displayed

### Requirement: Explorer search, sort, and view-mode toolbar
The Explorer SHALL provide a search input, a Plates / List / Map view-mode toggle, and a sort dropdown with options "Recently updated", "Catalog №", "Least complete first", "Most complete first".

#### Scenario: Free-text search
- **WHEN** the visitor types a substring into the search box
- **THEN** the result grid SHALL show only specimens whose `taxon`, `common`, `locality`, or `collector` (case-insensitive) contains the substring

#### Scenario: Sort by completeness ascending
- **WHEN** the visitor selects "Least complete first" from the sort dropdown
- **THEN** the result grid SHALL be ordered by `completeness` ascending

#### Scenario: View-mode toggle
- **WHEN** the visitor clicks "List" in the view toggle
- **THEN** the grid SHALL switch from card grid to a single-column list layout
- **AND** the toggle SHALL visually indicate "List" as the active mode

#### Scenario: Map view placeholder
- **WHEN** the visitor clicks "Map"
- **THEN** the toggle SHALL register the selection but the grid SHALL render a "Map view coming soon" placeholder (the map view is visual-only in v1)

### Requirement: Specimen card content
Each specimen card in the Explorer grid SHALL display the SVG plate image (with optional corner stamp showing the trailing catalog number), the `catalog` text, a status badge ("Verified" / "In review" / "Needs help"), the `taxon` (italicised), the `common` name, a meta line with `family · year · locality-head`, a 5-segment completeness bar with percent label, and the annotation count with pending count when greater than zero.

#### Scenario: Specimen with no pending annotations
- **WHEN** a card renders a specimen whose `pending` value is `0`
- **THEN** the "· N pending" suffix SHALL be omitted from the card foot

#### Scenario: Click opens annotation view
- **WHEN** the visitor clicks anywhere on a specimen card
- **THEN** the page SHALL transition to the Annotation view for that specimen
- **AND** the URL hash SHALL update to `#<specimen.id>`

### Requirement: Annotation view layout
The Annotation view SHALL render a top breadcrumb (`← Back to explorer › Kingdom › Family › Catalog`), a left image pane with viewer tabs (Full plate / Herbarium label / Specimen / Verso), zoom controls, an image rail with thumbnails and a "Recent annotators" stack, and a right-hand annotation panel with collapsible sections.

#### Scenario: Back to explorer
- **WHEN** the visitor clicks "← Back to explorer" in the breadcrumb
- **THEN** the page SHALL transition to the Explorer view
- **AND** the URL hash SHALL be cleared

#### Scenario: Region selection in viewer tabs
- **WHEN** the visitor clicks "Herbarium label" in the viewer tabs
- **THEN** the dark image stage SHALL show a yellow-bordered region overlay positioned over the bottom-right of the plate
- **AND** the overlay SHALL display a "Selected: handwritten label" tag

### Requirement: Annotation panel field sections
The right-hand annotation panel SHALL provide collapsible sections that mirror the field set in `app/templates/admin/unit-simple-entry.html`. Each section SHALL render `FieldRow` components with status (`verified` / `pending` / `empty` / `flagged`), each row showing label, value (or empty placeholder), contributor meta line when present, and hover-revealed action buttons ("Suggest edit" / "Annotate" / "Flag").

The panel SHALL include the following sections in order:
1. **Identification** — Scientific name (`taxon_id`), Common name, Type specimen toggle.
2. **Date** — Date collected (`collect_date` / `collect_date__year/month/day` / `verbatim_collect_date`), Date accessioned.
3. **Locality** — Place name (`named_area_country / adm1 / adm2 / adm3` joined), Coordinates (`latitude_*` / `longitude_*`), an inline minimap card, Elevation, Habitat.
4. **Handwritten label** — transcribe card with side-by-side "As written" handwritten sample and "Transcribed" textarea.
5. **Traits** — chip cluster (visual only in v1; no admin form equivalent).
6. **Flags & corrections** — at least one demo flag card and a "⚑ Raise a new flag" button.
7. **Notes** — free-text textarea with "Post note" primary button.

The panel SHALL also provide a tab strip (Annotate / History / Discuss) above the sections and a footer with a "Submit annotations" primary button. All write actions SHALL be visually present but inert in v1 (clicking SHALL NOT issue any network request).

#### Scenario: Section collapse
- **WHEN** the visitor clicks a section header
- **THEN** the section body SHALL toggle between expanded and collapsed
- **AND** the chevron SHALL switch between `−` and `+`

#### Scenario: Field with verified status
- **WHEN** a field row has `status="verified"` and a `contributor` object
- **THEN** the row SHALL render with a forest-green left border (3px)
- **AND** the meta line SHALL include "verified by N" text after the contributor name and timestamp

#### Scenario: Empty field placeholder
- **WHEN** a field row has no value and `status="empty"`
- **THEN** the row SHALL render with a dashed left border
- **AND** the value cell SHALL display "— not yet annotated —" in italic muted text
- **AND** the action button SHALL read "Annotate" (not "Suggest edit")

#### Scenario: Submit annotations is inert
- **WHEN** the visitor clicks "Submit annotations" in the panel footer
- **THEN** no network request SHALL be issued
- **AND** the button SHALL provide visual feedback only (e.g. brief active state)

### Requirement: Visual fidelity to nature-scribe design tokens
The implementation SHALL use the CSS custom properties from `nature-scribe/project/styles.css` (`--paper`, `--paper-2`, `--paper-card`, `--ink`, `--ink-2`, `--ink-3`, `--rule`, `--rule-soft`, `--oxblood`, `--forest`, `--gold`, `--moss`, `--serif`, `--body`, `--mono`, `--shadow-1`, `--shadow-2`) and SHALL load Cormorant Garamond, Lora, Caveat, and JetBrains Mono via Google Fonts.

#### Scenario: Token parity
- **WHEN** the annotate stylesheet is loaded
- **THEN** every CSS variable listed above SHALL be defined on `:root` (or scoped to `.annotate-shell`) with values matching the prototype's `styles.css`

#### Scenario: Font loading
- **WHEN** the `/annotate` page is rendered
- **THEN** a `<link rel="stylesheet" href="https://fonts.googleapis.com/...">` SHALL load all four font families with the weights used by the prototype (Cormorant Garamond 400/500/600 + italic 400/500, Lora 400/500 + italic 400, Caveat 400/500, JetBrains Mono 400/500)

### Requirement: Excluded design elements
The implementation SHALL NOT port the following elements from the prototype, since they are design-tool scaffolding rather than product features:
- The `TweaksPanel` floating sidebar
- The `darkArchive` mode toggle and the `.app-shell.dark` CSS rules
- The `accentHue` switcher and the `--accent-override` CSS variable
- The density (comfortable/compact) toggle
- The hardcoded "Eliza Marsh / 312 contributions" user chip in the topbar (replaced with a placeholder login affordance or omitted entirely until auth is wired)

#### Scenario: No tweaks panel in DOM
- **WHEN** the page is rendered
- **THEN** there SHALL be no element matching the selector `.tweaks-panel` (or any prototype tweak-panel class) in the DOM

#### Scenario: No dark mode rules in stylesheet
- **WHEN** `app/static/css/annotate.css` is inspected
- **THEN** it SHALL NOT contain any `.app-shell.dark` or `.dark` selector blocks
