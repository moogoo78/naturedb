## Why

NatureDB currently has no public-facing way for registered users to contribute to specimen records. Curators edit specimens through the admin interface, but there's no path for community contributors (volunteers, citizen scientists, visiting researchers) to flag errors, transcribe handwritten labels, or suggest field corrections. The "Nature-Scribe" design (handed off via `nature-scribe-handoff.zip`) sketches a paired Explorer + Annotation experience that solves this gap with a scholarly-archival visual language. Building it gives us a community-contribution surface without disrupting the existing admin/curation workflow.

## What Changes

- Add a new public route `/annotate` under the frontpage blueprint that renders an **Explorer** view: faceted left rail (Kingdom, Family, Region, Date, Annotation status, Completeness, Handwritten label), search/sort/view toolbar, and a grid of specimen cards.
- Add a paired **Annotation** view at `/annotate/<catalog>` (or driven by client-side state in v1): dark image stage with viewer tabs and zoom controls, plus a right-hand panel with collapsible sections matching the field set in `app/templates/admin/unit-simple-entry.html` (Identification, Date, Locality + minimap, Handwritten-label transcription, Traits, Flags, Notes).
- Implement the UI as **Jinja templates + vanilla JS modules** (no React, no build step). New JS modules live under `app/static/js/annotate/`; new CSS lives at `app/static/css/annotate.css` and ports the design tokens from `nature-scribe/project/styles.css`.
- **Mock data only in v1** — the page renders against a hard-coded `SPECIMENS` array shipped as a static JSON file (`app/static/js/annotate/specimens.mock.json`), ported from `nature-scribe/project/data.jsx`. No DB writes, no API calls, no auth gating yet.
- Skip the design's `TweaksPanel`, dark-archive toggle, accent-hue switcher, and the hardcoded "Eliza Marsh" user chip — those are design-tool scaffolding, not product features.

**Out of scope for this change** (deferred to follow-ups):
- Persisting annotations to the database (no `Annotation` model, no migration).
- Wiring auth / role checks for who can annotate.
- Replacing mock specimens with a real query against `Unit`/`Record`.
- IIIF integration, "Compare with similar", lightbox, real map (the minimap is a static SVG).

## Capabilities

### New Capabilities
- `annotation-explorer`: Public-facing two-screen UI (Explorer + Annotation view) for browsing specimens and viewing per-field annotation surfaces. Behaviour-level requirements cover routing, filter/search/sort interactions, the per-section field structure, and which design elements are intentionally omitted from the prototype.

### Modified Capabilities
<!-- None. This is purely additive; no existing spec's requirements change. -->

## Impact

- **New code**: `app/blueprints/frontpage.py` (one route handler + template-context helper), `app/templates/annotate/` (new directory with `explorer.html`, `annotation.html`, `_macros.html`), `app/static/css/annotate.css`, `app/static/js/annotate/*.js`, `app/static/js/annotate/specimens.mock.json`.
- **No backend model changes, no migrations, no API changes** in this change.
- **Fonts**: design uses Cormorant Garamond, Lora, Caveat, JetBrains Mono via Google Fonts. Add a single `<link>` in the new templates' `<head>` block (or `base.html` extension point). No npm dependencies.
- **No existing routes, models, or specs are modified.**
- **Risk**: low. The change is additive and isolated to a new URL prefix; it does not touch admin, search, or API code paths.
