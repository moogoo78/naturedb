## 1. URL Sync Utilities

- [x] 1.1 Create `syncUrlFromFilters(data)` function that takes the filter data object (from `getFormData()` plus `q`) and writes non-empty values to the URL querystring via `history.replaceState`
- [x] 1.2 Create `clearUrlFilters()` function that removes all filter params from the URL via `history.replaceState`

## 2. Write Filters to URL

- [x] 2.1 Call `syncUrlFromFilters()` at the end of `applyFilter()` in `data-search.html`, passing the current filter data plus the main search `q` value
- [x] 2.2 Call `clearUrlFilters()` from the clear/reset button handler in `_inc_filters_drawer.html`

## 3. Restore Filters from URL

- [x] 3.1 Create `restoreFiltersFromUrl()` async function that reads all querystring params and populates simple form fields (text inputs, date inputs, native selects)
- [x] 3.2 Restore TomSelect fields with static options (`family`, `collect_month`) by setting their value directly from querystring params
- [x] 3.3 Restore cascading taxonomy TomSelect fields in order: set `family` → await genus options fetch → set `genus` → await species options fetch → set `species`
- [x] 3.4 Restore cascading geography TomSelect fields in order: set `containent` → fetch country options → set `country` → await adm1 fetch → set `adm1` → await adm2 fetch → set `adm2` → await adm3 fetch → set `adm3`
- [x] 3.5 Restore `collector` TomSelect by fetching the collector record from the API and adding it as an option before setting the value
- [x] 3.6 Restore main search `q` value from querystring (extend existing logic that already reads `q`)

## 4. Auto-trigger Search on Load

- [x] 4.1 After `restoreFiltersFromUrl()` completes, call `applyFilter()` if any filter params were found in the URL

## 5. Multi-value Support

- [x] 5.1 Handle `collect_month` as comma-separated values in the URL (e.g., `collect_month=1,6,12`) — serialize on write, split on restore

