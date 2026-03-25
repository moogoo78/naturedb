# Collection Taxon Map

## Purpose

Each collection can be linked to specific taxon tree branches, so that taxon search and browsing only shows relevant taxa. For example, a plant herbarium sees only Plantae, a fish collection sees only Actinopterygii, even if they share the same backbone (e.g., TaiCOL).

## Data Model

```
collection_taxon_map
  id               PK
  collection_id    FK -> collection
  taxon_tree_id    FK -> taxon_tree
  taxon_id         FK -> taxon (nullable)
```

- `taxon_id` points to the root taxon of the branch (e.g., Plantae, Fungi, Actinopterygii)
- `taxon_id = NULL` means the whole tree is used (e.g., HAST-legacy tree where the top rank is family, with no higher taxon)
- A collection can have multiple rows to cover multiple branches

### Examples

| collection | taxon_tree | taxon_id | Meaning |
|---|---|---|---|
| HAST | TaiCOL | Plantae | Only plants from TaiCOL |
| HAST | TaiCOL | Fungi | Also fungi from TaiCOL |
| HAST | HAST-legacy | NULL | Whole legacy tree (top rank = family) |
| ASIZ | TaiCOL | Actinopterygii | Only ray-finned fish |

## Data Flow

### 1. Record Form — Taxon Search

```
User types in taxon field
       |
       v
JS sends to /api/v1/taxa
  filter: { q: "...", collection_id: X }
       |
       v
API: get_taxon_list()
  - Looks up collection_taxon_map for collection X
  - Gets tree_ids from the map
  - Filters: Taxon.tree_id IN (tree_ids)
  - Returns matching taxa
       |
       v
Select2 dropdown shows only relevant taxa
```

**Files:**
- `app/templates/admin/inc_record-form_script.js` — passes `collection_id` in filter
- `app/blueprints/api.py` — `get_taxon_list()` filters by mapped trees

### 2. Admin Searchbar

```
User types in searchbar
       |
       v
GET /admin/api/searchbar?q=...
       |
       v
api_searchbar()
  - Gets collection_ids from current_user.site
  - Looks up collection_taxon_map for those collections
  - Filters taxa by mapped tree_ids
  - Returns results
```

**File:** `app/blueprints/admin.py` — `api_searchbar()`

### 3. Taxon Tree Browser

```
GET /api/taxon-tree/trees?collection_id=X
       |
       v
Returns trees with their root taxa:
  { id, name, hierarchy, roots: [{ taxon_id, name }] }
       |
       v
GET /api/taxon-tree/children?collection_id=X&tree_id=Y
       |
       v
If parent_id is NULL (top level):
  - taxon_id set    -> start from that taxon (branch root)
  - taxon_id NULL   -> start from tree's top rank (e.g., family)
If parent_id given:
  - Normal child traversal via TaxonRelation (depth=1)
```

**File:** `app/blueprints/frontpage.py` — `taxon_tree_list()`, `taxon_tree_children()`

## Related Models

```
Collection  --<  CollectionTaxonMap  >--  TaxonTree
                       |
                       v
                     Taxon (root of branch, nullable)
                       |
                  TaxonRelation (closure table, depth)
                       |
                     Taxon (children)
```

## Files

| File | What |
|---|---|
| `app/models/collection.py` | `CollectionTaxonMap` model, `Collection.taxon_maps` relationship |
| `app/blueprints/api.py` | `/api/v1/taxa` — filter by `collection_id` |
| `app/blueprints/admin.py` | searchbar — filter taxa by collection trees |
| `app/blueprints/frontpage.py` | taxon tree browser — collection-aware |
| `app/templates/admin/inc_record-form_script.js` | passes `collection_id` to taxon search |
| `alembic/versions/cf68a46997e3_collection_taxon_map.py` | migration |
