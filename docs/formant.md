# Formant JavaScript lib toolkit for Form

For process form element, submit, filter tokens

Inspired from UIkit framework (like Web Component)

## backend API

should follow the rules:

```
api/filter={filterObject}&sort=[{field_name, -desc_field_name}]&range=[0, -1]
```

- filter: object (by key)
- sort: Array of sorted by field name (prefix with "-" for DESC)
- range: [start, end], if  [0,1] means no limit

## Design

- schema => 整理過的formData

## HTML arguments
- key: {filter key}
- label: {label}
- fetch: {API url}
- isFetchInit: fetch options initially
- query: {query string}
- sort: [foo, -bar]
- optionValue: {id}
- optionText: {text}
- changeTarget: {number} (needed for intensive)
- intensive|extensive: {number}, extensive use as range
- autocomplete: {q} (query field), autocomplete related render is customize only
- refName: refercence form name (for autocomplete id input)

## Library API
- register: set options, apply formant HTML argument to schema
- init: init default HTML option values
- setFilters
- removeFilter
- addFilters
- search
- getTokens
- setSearchParams
