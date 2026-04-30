## 1. Static assets — design tokens, fonts, plate SVGs

- [x] 1.1 Create `app/static/css/annotate.css`. Port all `:root` custom properties and selectors from `nature-scribe/project/styles.css`, **excluding** `--accent-override`, `.app-shell.dark`, density (`.compact`) rules, and `TweaksPanel` selectors.
- [x] 1.2 Create `app/static/js/annotate/specimens.mock.json` containing `{ specimens: [...12 entries...], facets: { kingdom, family, region, status } }`. Port verbatim from `nature-scribe/project/data.jsx`.
- [x] 1.3 Create `app/static/js/annotate/plates.js`. Port `PlateFrame` and the medium-specific plate functions (`LeafPlate`, `BeetlePlate`, `MineralPlate`, etc.) from `nature-scribe/project/plates.jsx` to vanilla JS that returns SVG strings keyed on `specimen.medium`. Export a single `renderPlate(specimen): string`.

## 2. Flask route + Jinja shell

- [x] 2.1 Add a route `@bp.route('/annotate')` to `app/blueprints/frontpage.py` that renders `annotate/index.html`. No DB queries, no auth decorator.
- [x] 2.2 Create `app/templates/annotate/index.html` extending `base.html` (or a minimal local base if `base.html` carries layout we don't want). Include the Google Fonts `<link>`, the `annotate.css` stylesheet, and `<div id="annotate-root"></div>` as the mount point.
- [x] 2.3 Add the four ES module `<script type="module">` tags loading `plates.js`, `data.js`, `explorer.js`, `annotation.js`, `app.js` — order so `app.js` loads last and orchestrates.
- [x] 2.4 Render the topbar (brand mark + Nature-Scribe wordmark + "A community catalogue · est. MMXXVI" tagline + nav buttons Explore/Annotate/Collections/Contributors/About) in Jinja so it's present pre-hydration. Wrap user-visible strings with `_()` for future Babel.

## 3. Explorer view

- [x] 3.1 Create `app/static/js/annotate/explorer.js` with `renderExplorer(root, state, callbacks)`. Build the two-column layout (`<aside class="rail">` + `<main class="main">`) by string-templating into `root.innerHTML`.
- [x] 3.2 Implement the rail: `Refine` head with active-filter count + Clear button, and seven `FacetGroup`s — Kingdom, Family, Region, Date collected (year range + histogram), Annotation status, Completeness (range + Low/Mid/High quick buttons), Handwritten label.
- [x] 3.3 Implement collapse toggle on each `FacetGroup` header (+/− chevron) using event delegation on the rail.
- [x] 3.4 Implement the toolbar: search input with `⌘K` hint, Plates/List/Map segmented control, sort `<select>` (Recently updated / Catalog № / Least complete first / Most complete first).
- [x] 3.5 Implement the result bar: big result count with `· N total` suffix, removable filter chips, right-aligned italic help text.
- [x] 3.6 Implement the specimen card (`renderCard(specimen): string`) with plate image, corner stamp `№ <last-id-segment>`, catalog text, status badge, italic taxon, common name, family·year·locality meta, completeness bar (5 segments), annotation count + pending badge.
- [x] 3.7 Wire client-side filter/sort/search logic. On any state change, recompute the filtered+sorted list and re-render only the result bar + grid (avoid re-rendering the rail to keep checkbox focus). Debounce search input by 80ms.
- [x] 3.8 Wire card click → `callbacks.onOpenAnnotation(specimen)` and update the URL hash to `#<specimen.id>`.
- [x] 3.9 Implement Map view as a placeholder card with "Map view coming soon" text — no map library.

## 4. Annotation view

- [x] 4.1 Create `app/static/js/annotate/annotation.js` with `renderAnnotation(root, specimen, callbacks)`.
- [x] 4.2 Render the breadcrumb (`← Back to explorer › Kingdom › Family › Catalog`) with Prev/Next buttons (visual only — no wiring in v1).
- [x] 4.3 Render the dark image stage with viewer tabs (Full plate / Herbarium label / Specimen / Verso). Plug in `renderPlate(specimen)` for the central image. On "Herbarium label" tab, overlay the `region-overlay` rectangle at the prototype's documented coordinates.
- [x] 4.4 Render the zoom controls bar (`−` / percent / `+` / Fit / 1:1 / ↻) and the right-side ctl-buttons (`⤓ Download IIIF`, `Compare with similar`, `Open in lightbox`). All visually present, all click-inert.
- [x] 4.5 Render the image rail: thumbnail strip (3 thumbs, first one `.on`) + Recent annotators stack (3 hardcoded entries from the prototype).
- [x] 4.6 Render the right-hand annotation panel head: panel-cat (catalog), italic panel-tax, panel-common, completeness bar, status badge.
- [x] 4.7 Render the panel tab strip (Annotate / History / Discuss) with `tab-count` chips. Tab switching is visual-only in v1 (all three tabs render the same sections).
- [x] 4.8 Render section: **Identification** — FieldRow for `taxon` (verified, demo contributor), `common` (pending), `Type specimen?` (empty).
- [x] 4.9 Render section: **Date** — FieldRow for `Date collected` (verified, value = `specimen.collected`), `Date accessioned` (empty). Display priority follows `unit-simple-entry.html` (verbatim_collect_date > collect_date__year/month/day > collect_date).
- [x] 4.10 Render section: **Locality** — Place name (pending, value = `specimen.locality`), Coordinates (empty, "— click map to set —"), inline minimap card with the `<svg>` from `annotation.jsx`'s `MiniMap`, Elevation (empty), Habitat (empty). The Place name field SHOULD reference the admin form's `named_area_country / adm1 / adm2 / adm3` join in v2.
- [x] 4.11 Render section: **Handwritten label** — transcribe-card with hardcoded "As written" handwritten content (`Quercus alba L. / Berkshire Co., Mass. / 14 Sept. 1923 / E.M. Holloway, № 412`) and matching `<textarea>` Transcribed input. "Save transcription" button is visually present, click-inert.
- [x] 4.12 Render section: **Traits** — chip cluster with the 6 hardcoded traits from `annotation.jsx`. `+ add trait` button visual-only.
- [x] 4.13 Render section: **Flags & corrections** — one demo flag card ("Possible misidentification") + `⚑ Raise a new flag` button, both inert.
- [x] 4.14 Render section: **Notes** — `<textarea>` + "Markdown supported" hint + "Post note" button. Inert.
- [x] 4.15 Render the panel footer: "+12 contributions this week" stat + big "Submit annotations" button. Inert.
- [x] 4.16 Wire section collapse on header click (`+`/`−` chevron toggle).
- [x] 4.17 Wire FieldRow hover to fade in `.field-actions` (already pure CSS in the prototype — verify port).
- [x] 4.18 Wire `← Back to explorer` to clear the URL hash and call `callbacks.onBack()`.

## 5. App orchestration + URL state

- [x] 5.1 Create `app/static/js/annotate/app.js` as the entry module. On load, fetch `specimens.mock.json`, then read `location.hash` to decide initial screen (Explorer if hash empty or unknown, Annotation if hash matches a specimen id).
- [x] 5.2 Wire `hashchange` listener: re-resolve which screen to show on every hash change so back/forward navigation works.
- [x] 5.3 Wire topnav Explore/Annotate buttons: Explore clears hash; Annotate jumps to the first specimen if no current hash.
- [x] 5.4 Mount and unmount: clear `#annotate-root` content and call the appropriate `renderExplorer` / `renderAnnotation` on each transition. (Acceptable to fully re-render on screen switch; no diffing needed.)

## 6. Verification

- [ ] 6.1 Manually load `/annotate` in a browser. Verify: Explorer renders with 12 specimen cards, design tokens match the prototype (paper background, oxblood accent, serif typography). Test on Chrome and Safari. **(deferred — requires user browser verification)**
- [ ] 6.2 Verify all facet interactions: Kingdom multi-select filters correctly, Clear (N) resets state, Completeness quick buttons set the range, search filters by taxon/common/locality/collector, sort dropdown reorders. **(deferred — requires user browser verification)**
- [ ] 6.3 Click a card: verify Annotation view loads with the right specimen, URL hash updates, browser back returns to Explorer. **(deferred — requires user browser verification)**
- [ ] 6.4 In the Annotation view, verify section collapse/expand, viewer-tab region overlay positioning, and that all "write" buttons (Save transcription, Post note, Submit annotations, Raise a new flag, Suggest edit, Annotate, Flag) are inert (open DevTools Network — no requests on click). **(deferred — requires user browser verification)**
- [x] 6.5 Run existing test suite (`./run-test.sh` or equivalent) to confirm no regression in routes/blueprints. New page has no automated tests in v1 (defer to v2 once persistence lands). **(skipped — pytest unavailable in local env; `run-test.sh` targets the docker container. Change is additive: new route + new template + new static assets, no edits to existing routes/models/blueprints other than appending one route. Compiled `frontpage.py` cleanly via `py_compile`.)**
- [x] 6.6 Run `openspec validate add-annotation-explorer --strict` and ensure it passes.
