## 1. Configuration

- [ ] 1.1 Add `SCRIBE_COLLECTION_LABELS` dict to `Config` in `app/config.py`. Seed with `{1: 'HAST:vascular', 2: 'HAST:alga', 3: 'HAST:fungi', 4: 'HAST:lichen', 5: 'PPI', 6: 'BISH:sample_material', 7: 'BISH:barcode', 8: 'ASIZ:fossil'}`.

## 2. Backend: shaping helper

- [ ] 2.1 Create `app/exporters/scribe.py` with `shape_specimen_row(unit_row, family_map, kingdom_map, cover_url_map)` returning the card-shaped dict. Mirror the batch-fetch pattern in `app/exporters/tbia.py`.
- [ ] 2.2 Implement `shape_specimens_page(units, records, *, collection_id_to_label)` that takes a page slice and runs the three batch queries (taxon family/kingdom ancestors via `TaxonRelation`, cover-image URLs via `MultimediaObject`).

## 3. Backend: API endpoints

- [ ] 3.1 Add `@api.route('/scribe/collections')` returning `{items: [{id, label, count}], total}` from a single `JOIN` of `collection` to `unit` with `GROUP BY collection.id` and `ORDER BY count DESC`. Filter to `id IN SCRIBE_COLLECTION_LABELS` (so newly created or hidden collections don't leak). Map `id → label` from the config dict.
- [ ] 3.2 Add `@api.route('/scribe/specimens')` accepting `collection_id`, `q`, `sort`, `page` (default 1), `per_page` (default 50, clamped to [1, 100]). Return `{items: [...], page, per_page, total}`. Build the query with `select(Unit, Record).join(Record).where(Unit.collection_id == ...)`, apply `q` as a case-insensitive `OR` over `proxy_taxon_scientific_name`, `proxy_taxon_common_name`, `locality_text`, `verbatim_collector`, apply `sort` (`recent` → `Unit.id DESC`, `catalog` → `Unit.catalog_number ASC`, `completeness-asc/desc` deferred — fall back to `recent`).
- [ ] 3.3 In the `/specimens` handler, fetch the page rows first, then call the batch-shape helper from 2.2 to attach kingdom/family/cover_url. Return shaped dicts.

## 4. Frontend: data plumbing

- [ ] 4.1 In `app/templates/annotate/index.html`, replace `data-static-url=...specimens.mock.json` with `data-api-base="/api/v1/scribe"` on `#annotate-root`.
- [ ] 4.2 In `app/static/js/annotate/app.js`, replace the static-JSON fetch with a small `api(path, params)` helper. Maintain explorer state (`{collection_id, q, sort, page, per_page}`) at the app level; refetch `/specimens` whenever any of those change. Fetch `/collections` once on first paint.

## 5. Frontend: rail facet group + pagination UI

- [ ] 5.1 In `app/static/js/annotate/explorer.js`, add a new `renderInstitutionFacet(collections, selectedId)` that renders a radio-style list (single-select) at the top of the rail. The label parses on `:` to render org-vs-sub-collection styling.
- [ ] 5.2 Mark the existing facet groups (Kingdom, Family, Region, etc.) as inert: keep the markup, drop the `change` handler wiring for those checkboxes (or short-circuit the handler so it does nothing). Leave the toolbar search and sort wired — they call into a new `onParamsChanged` callback that triggers an API refetch.
- [ ] 5.3 Add pagination UI below the grid: `‹ Prev   Page N of M   Next ›`. Disable Prev on page 1 and Next when `page * per_page >= total`.

## 6. Annotation detail view

- [ ] 6.1 Annotation view continues to read from the in-memory mock dataset for now. Confirm the card click → annotation transition still works after the explorer rewires (the click handler was passing the full specimen object; the new flow passes the shaped row from the API response, which has the same field set).

## 7. Verification

- [ ] 7.1 `curl 'http://localhost:5000/api/v1/scribe/collections' -H 'Host: scribe.sh21.ml'` returns 200 with the 8 seeded collections, ordered by unit count.
- [ ] 7.2 `curl 'http://localhost:5000/api/v1/scribe/specimens?collection_id=1&page=1&per_page=10' -H 'Host: scribe.sh21.ml'` returns 200 with 10 shaped items.
- [ ] 7.3 Browser smoke test on `http://scribe.sh21.ml:5000/`: rail shows the Institution/Collection group; clicking `HAST:vascular` populates the grid; pagination Next/Prev moves through pages; search box filters server-side; sort dropdown reorders results; clicking a card still opens the (mock) annotation view.

## 8. Documentation

- [ ] 8.1 Update `openspec/specs/annotation-explorer/spec.md` after this change archives, replacing the "no DB access" requirement with the live-API requirement and adding the institution+collection facet requirement.
