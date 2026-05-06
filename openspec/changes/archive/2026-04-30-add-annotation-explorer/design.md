## Context

The `nature-scribe-handoff.zip` design bundle ships a React/JSX prototype for a community-annotation experience. The user has chosen to ignore the React prototype's structure and rebuild the visual output on the existing Flask/Jinja + vanilla-JS stack already used elsewhere in the app (`app/templates/`, `app/static/js/`, `app/static/css/`). The existing public surface is mostly server-rendered Jinja with sprinkled JS; the only Svelte SPAs (`client/data-search/`, `client/admin-record/`) are explicitly out of scope.

V1 is a **visual port with mock data**. No DB writes, no auth gating, no API calls. The data model and write paths are deferred to a follow-up change so we can land the UI and iterate on the design before committing to a schema.

The annotation panel's field set is anchored on `app/templates/admin/unit-simple-entry.html`, so the same fields curators edit (catalog number, collector, field number, verbatim collect date, structured collect date, taxon, lat/long, named-area country/adm1/adm2/adm3, history notes) are also the fields registered users will eventually be able to annotate.

## Goals / Non-Goals

**Goals:**
- Render the Explorer screen pixel-equivalent to `nature-scribe/project/Nature-Scribe.html` + `explorer.jsx` + `styles.css` using server-rendered Jinja and vanilla JS modules.
- Render the Annotation screen with the same visual fidelity, with section content driven by the field set in `unit-simple-entry.html`.
- Keep the implementation isolated: one new route, one new template directory, one new CSS file, one new JS module directory, one mock JSON file. No edits to admin, search, API, or model code.
- Support keyboard-friendly faceted filtering and sort/search interactions client-side against the mock dataset.

**Non-Goals:**
- Persisting annotations (no `Annotation` SQLAlchemy model, no migration, no POST endpoints).
- Replacing mock specimens with `Unit`/`Record` query results.
- Auth / role gating. The page is reachable by anyone in v1 — the "registered user" requirement is enforced in a follow-up change.
- IIIF tile serving, real map tiles, "Compare with similar", lightbox, image annotation overlays beyond the static design's selected-region rectangle.
- Porting `TweaksPanel`, dark-archive mode, accent-hue switcher, density toggle. These are design-tool scaffolding.
- Internationalisation of new strings beyond what's already wired through Flask-Babel (we'll wrap user-visible strings in `_()` so a follow-up translation pass is cheap).

## Decisions

### D1: Stack — Flask blueprint + Jinja templates + vanilla ES module JS
**Choice**: Add the route to the existing `app/blueprints/frontpage.py` blueprint. Templates live under a new `app/templates/annotate/` directory. Client-side logic lives in `app/static/js/annotate/` as ES modules loaded with `<script type="module">`. CSS is a single `app/static/css/annotate.css`.
**Why**: Matches the rest of the public site's stack. No build step, no new dependencies, no Vite config to maintain. The user explicitly chose this over the existing `client/data-search/` Svelte SPA pattern.
**Alternatives considered**: (a) New `client/data-explorer/` Svelte/Vite app — rejected by user. (b) Jinja shell + Vite-bundled vanilla JS — rejected for build complexity. (c) Drop the React HTML in static/ as-is — rejected because the prototype loads `@babel/standalone` from a CDN and isn't suitable for production.

### D2: Mock data shipped as a static JSON file
**Choice**: Port the `SPECIMENS` and `FACETS` arrays from `nature-scribe/project/data.jsx` to `app/static/js/annotate/specimens.mock.json`. The JS module fetches it on page load. Field names match the prototype (`catalog`, `kingdom`, `taxon`, `common`, `family`, `collector`, `collected`, `locality`, `completeness`, `annotations`, `pending`, `status`).
**Why**: Lets us land the UI without coupling to the SQLAlchemy schema. The follow-up "wire to real data" change will replace the fetch URL with a real API endpoint that returns the same shape (or a documented superset).
**Alternatives considered**: (a) Embed the array inline in a `<script>` tag — rejected because we want the swap-to-real-API to be a one-line URL change. (b) Hard-code in Python and pass through the template — rejected for the same reason; keeping data fetch on the client makes the API boundary explicit.

### D3: Catalog routing — single page, client-side state
**Choice**: One Flask route `/annotate` renders an Explorer-first shell. The Annotation view is rendered into the same shell when the user clicks a card; the URL updates to `/annotate#<catalog>` (hash-based) so back/forward and deep links work without server round-trips.
**Why**: Mock data lives on the client; there's nothing to fetch when switching specimens. Hash-based routing avoids needing a second Flask handler. When v2 wires real data, we can promote it to History API path-based routing (`/annotate/<catalog>`).
**Alternatives considered**: (a) Separate `/annotate` and `/annotate/<catalog>` routes — defers cleanly to v2 but adds complexity now. (b) No URL persistence — fails the "deep link to a specimen" UX expectation.

### D4: SVG plates — port `plates.jsx` to a small JS module
**Choice**: Translate `plates.jsx`'s `PlateFrame` + medium-specific plate functions (`LeafPlate`, `BeetlePlate`, etc.) to a vanilla JS module that returns SVG strings (or DOM nodes) keyed on `specimen.medium`. Render server-side as a Jinja macro is **not** chosen because the SVGs are deterministic from data and the JS port keeps the prototype-to-impl mapping 1:1 for visual review.
**Why**: SVG output is identical regardless of the host language; keeping it in JS lets us use `innerHTML` directly and avoids a Python<>JS port mismatch.
**Alternatives considered**: Render plates as static PNGs in `app/static/sites/` — rejected because the design uses 12 different plate styles per medium and we don't want to maintain 12 binaries.

### D5: Field set sourced from `unit-simple-entry.html`
**Choice**: The Annotation view's collapsible sections are anchored to the field set in the admin entry form:
- **Identification** → `taxon_id`, plus a derived "common name" and a "type specimen?" toggle (visual-only).
- **Date** → `verbatim_collect_date`, `collect_date__year/month/day`.
- **Locality** → `named_area_country / adm1 / adm2 / adm3`, `latitude_*`, `longitude_*`, plus a static minimap SVG.
- **Handwritten label** → transcribe-card UI mapped to a hypothetical "verbatim label" field (no admin equivalent today; documented as a v2 backend addition).
- **Traits** → no admin equivalent in `unit-simple-entry.html`; rendered as visual-only chips for now.
- **Flags & Notes** → maps to the form's `history_note` / general remarks block.
**Why**: Aligns the annotation surface with the curator surface so when v2 wires persistence, the same fields are editable from both ends. Documents the gap (Traits, Verbatim Label) explicitly so v2 either adds them to the model or drops them.
**Alternatives considered**: Implement only fields that have a 1:1 admin counterpart — rejected because it strips the design of half its visual surface.

### D6: Skip the design's "scaffolding"
**Choice**: Do not implement `TweaksPanel`, `darkArchive` toggle, `accentHue` switcher, density toggle, or the hardcoded "Eliza Marsh / 312 contributions" user chip.
**Why**: These are claude.ai/design tooling for the prototype reviewer, not product features. Including them would add ~30% of the surface area and ~0% of the user value.
**Visible consequence**: The CSS variable `--accent-override` is dropped; oxblood is the fixed accent. `.app-shell.dark` rules are dropped from `annotate.css`.

### D7: Fonts via Google Fonts `<link>` in the new template
**Choice**: Load Cormorant Garamond, Lora, Caveat, JetBrains Mono via the same `<link rel="stylesheet">` URL the prototype uses, scoped to the annotate templates only (not added to `base.html`).
**Why**: Avoids changing the typography of the rest of the site. Self-hosting the fonts is preferable long-term but defers cleanly.

## Risks / Trade-offs

- **[Risk]** Visual drift from the prototype as we translate JSX to plain DOM → **Mitigation**: keep `nature-scribe/project/styles.css` as the canonical CSS source; copy class names verbatim and only rename if there's a Jinja/CSS conflict. Diff the rendered HTML structure against the prototype as a review step.
- **[Risk]** Mock JSON shape drifts from real `Unit`/`Record` shape, making v2 wire-up painful → **Mitigation**: in v2, the real API endpoint will reshape DB rows into the documented mock shape; this change is the schema's source of truth until then. Document the shape in `specimens.mock.json` as a top-level comment.
- **[Risk]** "Public, no auth" v1 lets anyone hit the page in production → **Mitigation**: the page renders only mock data and has no write paths, so the blast radius is zero. We can also gate the route behind a feature flag or `if current_app.debug` if the user wants belt-and-braces. (Open question — see below.)
- **[Trade-off]** No build step means no minification / tree-shaking. The CSS is ~25KB and the JS is expected to be ~15KB total — well within budget for a server-rendered page.
- **[Trade-off]** Hash-based routing means the URL bar shows `/annotate#NHM-2013-0421` instead of `/annotate/NHM-2013-0421`. Acceptable for v1; v2 upgrades to History API.

## Migration Plan

Pure additive change — no data migration, no breaking changes. Deploy is a single PR merge. Rollback is `git revert`. No feature flag required because the route does not exist before this change.

## Open Questions

1. **Should the v1 route be gated behind a feature flag or auth check** (e.g. `@login_required`) so it doesn't appear publicly until v2 wires real data and persistence? Current default: leave it public-but-unlinked (no nav entry added in `base.html`), so it's reachable by direct URL but not advertised.
2. **Should the new fonts be added to `base.html`** so the rest of the site picks them up, or scoped only to `/annotate`? Current default: scoped only.
3. **Top-nav entry**: the design's top bar shows "Explore / Annotate / Collections / Contributors / About". For v1 we render the bar but only `Explore` and `Annotate` are wired (toggling the two views). Collections/Contributors/About are visual-only buttons. Confirm acceptable.
