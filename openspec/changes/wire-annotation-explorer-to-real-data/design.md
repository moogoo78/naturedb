## Decision: two endpoints (`/scribe/collections` + `/scribe/specimens`), not a single batched response

**Choice**: Expose two endpoints. `/collections` returns the rail facet (one row per collection with label + unit count). `/specimens` returns the paginated grid (one row per Unit). The Explorer fetches `/collections` once on first paint and refetches `/specimens` on every filter / search / sort / page change.

**Why**:
- Independent cache lifecycles. The collection list changes maybe once a quarter; the specimen page changes on every interaction. Bundling them would invalidate the collection list every time a user pages.
- Clean URLs to point at downstream tooling later (link a contributor straight at `?collection_id=2`).
- Lets us add per-collection metadata to `/collections` later (taxonomic scope, latest activity) without bloating the per-row specimen payload.

**Alternatives considered**:
- *Single `/scribe/explorer` endpoint that returns both*: simpler client code, but couples cache invalidation and makes the response harder to reuse.
- *GraphQL*: overkill for two read-only endpoints.

## Decision: hard-coded `Config.SCRIBE_COLLECTION_LABELS` dict keyed by `collection.id`

**Choice**: Map `collection.id → display string` in `app/config.py`, e.g. `{1: 'HAST:vascular', 5: 'PPI', …}`. The "PPI as bare org code" pattern is encoded by just writing `'PPI'` (no colon) for that row; the rendering code splits on `:` for label tag styling and treats absence of colon as "single-line label".

**Why**:
- The user gave concrete examples (`HAST:vascular`, `HAST:alga`, `PPI`) but those labels have no source-of-truth in the existing schema. `collection.label` carries human-friendly Chinese names ("HAST-藻類") that aren't usable as facet keys.
- A dict keeps each row's display behavior data, not logic. To change `PPI` to `PPI:default` later, edit one tuple — no `if collection.label == "default"` shenanigans.
- The set of collections is small (8 today, ~10s long-term) and changes rarely; a hardcoded dict is the lowest-overhead representation.

**Alternatives considered**:
- *Add a `display_key` column on `collection`*: more flexible but requires a migration and admin UI for what is currently a one-page text file. Defer until we actually need per-deploy customization.
- *Derive from `org.code` + `collection.name` with a sub-collection rule*: works for HAST (where `name` is `algae`/`fungi`/`lichen`), breaks for PPI (`name='ppi'`, would produce `PPI:ppi`). Not worth the special-casing.

## Decision: server-side pagination with `page` + `per_page`, max 100 per page

**Choice**: `/specimens?collection_id=1&page=3&per_page=50`. The server returns `{items: [...], page, per_page, total}`. `per_page` is clamped to `[1, 100]` to bound query cost. The UI defaults to 50 per page with prev/next buttons; jump-to-page can land later.

**Why**:
- 134 730 HAST units rules out client-side pagination of a full payload.
- Cursor pagination would be more correct (no skipped/duplicated rows under writes) but is overkill for an explorer used by humans browsing — `LIMIT/OFFSET` over a stable `Unit.id DESC` order is good enough and trivially supports "Page 5 of 2245" later.
- 100 is the cap because shaping each row touches the related Record, taxon ancestor walk, and cover image lookup. Past ~100 the request budget eats into the 250ms p95 target.

**Alternatives considered**:
- *Cursor pagination*: deferred until we hit actual ordering artifacts.
- *Infinite scroll only*: makes deep-linking awkward and forces the client to remember which pages it loaded.

## Decision: stub the mock-only card fields from real columns rather than dropping them

**Choice**: `status`, `completeness`, `pending`, `medium`, `color` keep their slots in the API response. They are derived from real columns:
- `status`: `'verified'` if `unit.pub_status='P'`, else `'in-review'`.
- `completeness`: percentage of populated key columns out of 7 (taxon, common, family, collector, collected, locality, catalog_number).
- `pending`: fixed at 0 (no real source yet).
- `medium`: `kingdom_to_medium[kingdom]` (e.g. `Plantae→leaf`, `Animalia→insect`, `Mineralia→mineral`, `Fungi→mushroom`); falls back to `'specimen'` when kingdom is unknown.
- `color`: `kingdom_to_color[kingdom]`.

**Why**: the existing card template, plate SVG renderer, and status badge styling all key off these fields. Dropping them would require touching `explorer.js`, `plates.js`, and `annotate.css` — a larger surface than this change wants. Stubs let the cards keep rendering and signal where v2 should plug in real curation/QC signals.

**Alternatives considered**:
- *Drop the fields entirely and simplify the card*: cleaner long-term, but turns this change into a UI rewrite. Defer to a future "real curation status" change.

## Decision: server-side `q` and `sort`; other rail facets stay inert

**Choice**: The search input and sort dropdown wire through to the API as `q=` and `sort=`. The other rail facet groups (Kingdom, Family, Region, Date, Status, Completeness, Handwritten) keep their current rendered state but stop emitting filter mutations — selecting a kingdom checkbox no longer changes the grid.

**Why**: The user explicitly asked for this scoping. Search and sort are essential for any usable list view at this size; bypassing them server-side would turn the search box into a "filter the current page only" affordance which is worse than no search box. The other facets aren't trivially derivable yet (kingdom requires a taxon-ancestor walk; family is derivable but counts need their own GROUP BY; region requires the named_area gazetter), so the cost of wiring them outweighs v1 value.

**Alternatives considered**:
- *Hide the inert facets entirely*: more honest UI, but the user wants the layout preserved. Easier to switch on later than to redesign the rail.

## Decision: deferred auth, host-gated UI only

**Choice**: Both endpoints are anonymous-readable. The page itself is already host-gated to `SCRIBE_HOSTS` by the frontpage preprocessor; the API is not. Anyone can curl `/api/v1/scribe/specimens` from any host.

**Why**: The user explicitly deferred auth ("do auth later, just ignore it"). The data exposed is the same data already public via existing search APIs, so there's no privacy regression. We accept that callers can hit the API without going through the scribe page.

**Open question for follow-up auth change**: should `/scribe/*` API endpoints reject when `Host:` is not in `SCRIBE_HOSTS`, mirror the page-level gating, or rely on JWT once we add it? Track in a separate change.

## Risks / Trade-offs

- **Inert facets in the rail are misleading.** A user clicking a Kingdom checkbox will see no change in results, which feels broken. We're betting they read the `Institution / Collection` group as the active filter and ignore the rest until we wire them. Mitigated by leaving the existing UI ordered with Institution/Collection at the top.
- **Stub fields look authoritative but aren't.** A `status="verified"` badge on every public unit will be misleading for collections that haven't been curated. Acceptable for an internal-facing v2; revisit before linking from `base.html` nav.
- **N+1 risk on /specimens shaping.** Naive per-row family/kingdom lookups would dominate the response time. The change includes `app/exporters/scribe.py` with the same batch-fetch pattern proven in `app/exporters/tbia.py` (commit 251ab88 took occurrence harvesting from 26s → ~1s by exactly this).
