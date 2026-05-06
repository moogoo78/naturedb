## Why

The annotation explorer at `scribe.naturedb.org/` currently renders against a 12-row static JSON file (`app/static/js/annotate/specimens.mock.json`). To make Scribe usable as a real annotation surface, the specimen grid needs to bind to live `Unit` / `Record` data. The first piece of live data we want to expose is the institution + collection facet, so volunteers can pick the herbarium they want to work in (e.g. `HAST:vascular`, `HAST:alga`, `PPI`).

## What Changes

- **API**: add two anonymous-readable JSON endpoints under `/api/v1/scribe/` — `GET /collections` (institution+collection list with display labels and unit counts) and `GET /specimens` (paginated, server-filtered by `collection_id`, `q`, `sort`).
- **Config**: add `Config.SCRIBE_COLLECTION_LABELS`, a hard-coded dict keyed by `collection.id` mapping to display strings (`{1: 'HAST:vascular', 2: 'HAST:alga', …, 5: 'PPI'}`). The `PPI` row demonstrates the "single-collection org → bare org code" pattern by simply mapping to a label without a colon suffix; the rule is data, not logic.
- **Explorer UI**: add a new "Institution / Collection" facet group at the top of the rail, populated from `/collections`. Selecting an entry sets `collection_id` and re-fetches specimens. Other rail facet groups (Kingdom, Family, Region, Date, Status, Completeness, Handwritten label) remain visually present but become **inert** in this iteration — they no longer drive client-side filtering of the live grid.
- **Data binding**: `app.js` replaces the static `specimens.mock.json` fetch with live API calls. The `q` search box and `sort` dropdown wire through to the API. The grid renders one *page* of results at a time (default 50 per page) with prev/next controls, since a single collection can hold >130 k units.
- **Stub fields**: card fields the DB doesn't carry directly (`status`, `completeness`, `pending`, `medium`, `color`) are derived as stubs from real columns (status from `Unit.pub_status`; completeness from a count of populated key columns; pending fixed at 0; medium/color from a kingdom→preset map) so the existing card layout keeps working without UI changes.
- **Annotation detail view** stays mock in this iteration. Clicking a card still opens the same per-specimen template wired to the mock dataset.

## Capabilities

### Modified Capabilities
- `annotation-explorer`: the data-source requirement flips from "static JSON, no DB" to "paginated DB-backed JSON API". The "no DB access" scenario is replaced with a paginated-fetch scenario.

### New Capabilities (none — all deltas land inside `annotation-explorer`)

## Impact

- **Code**: `app/config.py` (new constant), `app/blueprints/api.py` (two new route handlers), `app/exporters/scribe.py` (new module that batch-fetches the relations needed to shape specimen rows, mirroring the `tbia.py` pattern for the same problem on the TBIA harvester), `app/static/js/annotate/app.js` (replace fetch source, add pagination state), `app/static/js/annotate/explorer.js` (new facet group, server-driven filter/search/sort, pagination controls).
- **Templates**: `app/templates/annotate/index.html` — `data-static-url` attribute repurposed to `data-api-base` pointing at `/api/v1/scribe`.
- **Static**: `specimens.mock.json` stays in place because the annotation detail view still consumes it; it can be deleted in a follow-up change.
- **Performance**: with 134 k HAST units, naive shaping is too slow per request. Same batch-fetch pattern as `app/exporters/tbia.py` (one query for cover images, one for taxon kingdom ancestors, one for the page slice) keeps the typical response under ~150 ms. Facet counts on `/collections` are a single `GROUP BY` over `unit.collection_id` and are cheap.
- **Auth**: deferred. Both endpoints are anonymous-readable in this iteration. Host-gating already restricts the UI itself to scribe subdomains, but the API blueprint is reachable on portal/site hosts too — in practice the URLs only get called from the scribe page, but a follow-up change should fold scribe-host gating (or a public-API decorator) into the endpoints.
- **Failure modes**: the explorer must render gracefully when `/collections` returns zero rows (empty rail group with a "No collections" placeholder) and when `/specimens` returns zero rows for the active filter (existing empty-grid behavior).
