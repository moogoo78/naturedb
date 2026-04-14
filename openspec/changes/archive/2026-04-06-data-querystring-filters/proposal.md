## Why

When users apply filters on the `/data` search page (via the main search box or advanced filters drawer), the filter state is lost on page refresh or when sharing the URL. Currently, only the `q` parameter is read from the querystring on page load — all other filters (taxon, collector, named areas, accession number ranges, dates, etc.) are purely in-memory. This makes it impossible to bookmark, share, or navigate back to a filtered result set.

## What Changes

- Sync all active filter values to the browser URL querystring when a search is applied
- On page load, read querystring parameters and restore all filter form fields (including TomSelect comboboxes) to their saved state, then auto-trigger the search
- Update the URL (via `history.replaceState`) each time filters change, without full page reload
- Support the existing `q` parameter plus all advanced filter fields: `collection`, `type_status`, `family`, `genus`, `species`, `collector`, `field_number`, `field_number2`, `accession_number`, `accession_number2`, `collect_date`, `collect_date2`, `collect_month`, `country`, `adm1`, `adm2`, `adm3`, `altitude`, `altitude2`, `altitude_condiction`, `containent`
- Clear querystring when filters are reset via the "clear" button

## Capabilities

### New Capabilities
- `querystring-filter-sync`: Bidirectional sync between the filter form state and the browser URL querystring on the `/data` page

### Modified Capabilities

## Impact

- **Frontend only**: `app/templates/data-search.html` and `app/templates/_inc_filters_drawer.html` (JavaScript changes)
- No backend/API changes required — the filter-to-API-request flow already works, this just persists the filter inputs in the URL
- TomSelect comboboxes need special handling: restoring their state requires fetching options from the API before setting values
