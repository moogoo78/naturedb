## Context

The `/data` search page uses a Grid.js table with server-side pagination/sorting and a Flowbite drawer containing advanced filters powered by TomSelect comboboxes. When users apply filters, a JSON `filter` parameter is sent to `/api/v1/search`. Currently only the `q` querystring parameter is read on page load — all other filter state lives only in JavaScript memory and is lost on refresh, back-navigation, or URL sharing.

The filter form fields include simple inputs (text, date, select) and TomSelect comboboxes that load options dynamically from the API (genus depends on family, species depends on genus, adm1/2/3 cascade from country, collector is remote-searched).

## Goals / Non-Goals

**Goals:**
- Persist all filter values in the URL querystring so searches are bookmarkable and shareable
- Restore filter form state from querystring on page load, including cascading TomSelect fields
- Auto-trigger search when querystring filters are present on load
- Keep the URL in sync as filters change (without page reload)
- Clear querystring when filters are reset

**Non-Goals:**
- Persisting view mode (table/list/gallery tab) in the URL
- Persisting pagination state or sort order in the URL
- Browser history entries per filter change (use `replaceState`, not `pushState`)
- Modifying backend/API behavior

## Decisions

### 1. Flat querystring keys matching form field names

Use the form field `name` attributes directly as querystring keys (e.g., `?family=123&genus=456&collector=78`). This keeps the URL human-readable and avoids a JSON blob in the URL.

**Alternative considered**: Encoding the entire filter as a single JSON `filter=` param. Rejected because it produces unreadable URLs and is harder to manually edit or debug.

### 2. Use `history.replaceState` to update URL

Replace the current history entry rather than pushing new ones. This avoids polluting the browser back button with every filter tweak.

### 3. Restore TomSelect fields via sequential async initialization

Cascading comboboxes (family → genus → species, country → adm1 → adm2 → adm3) require their parent's options to be loaded before the child can be set. On page load with querystring params, the restore logic must:
1. Set the parent value and wait for its `onChange` to fetch child options
2. Then set the child value
3. Continue down the cascade

This will use async/await with the existing `fetchOptions` helper.

### 4. Single `syncUrlFromFilters()` function called from `applyFilter()`

Rather than watching each input individually, call one function after `getFormData()` that writes all current filter values to the URL. This is simpler and keeps the sync point centralized.

### 5. Single `restoreFiltersFromUrl()` function on DOMContentLoaded

One async function reads all querystring params and populates form fields in dependency order, then triggers `applyFilter()` if any params were found.

## Risks / Trade-offs

- **TomSelect restore complexity** → The cascading selects require fetching API data before values can be set. Mitigation: restore in strict dependency order with awaits; show a brief loading state if needed.
- **URL length limits** → With many filters active, URLs could get long. Mitigation: only include non-empty values; practical filter combinations are unlikely to exceed browser limits (~2000 chars).
