# Collection–Taxon Tree Mapping

## Overview

Each site in NatureDB hosts one or more collections (e.g. HAST, HAST-藻類, Fossil). The system supports multiple taxon trees (e.g. HAST-legacy, TaiCOL). The `collection_taxon_map` table controls which taxon tree(s) each collection uses, so that admin and frontend views only show relevant taxa.

## Data Model

### Table: `collection_taxon_map`

| Column          | Type    | Description                                                                 |
|-----------------|---------|-----------------------------------------------------------------------------|
| `id`            | Integer | Primary key                                                                 |
| `collection_id` | Integer | FK → `collection.id`. Which collection this mapping belongs to.            |
| `taxon_tree_id` | Integer | FK → `taxon_tree.id`. Which taxon tree this collection uses.               |
| `taxon_id`      | Integer | FK → `taxon.id` (nullable). Optional root taxon to scope to a branch. NULL means the entire tree. |

A collection can have multiple mappings — e.g. both Plantae and Fungi branches from the same tree. A NULL `taxon_id` means the collection uses the whole tree.

### Relationships

- `Collection.taxon_maps` → list of `CollectionTaxonMap`
- `CollectionTaxonMap.collection` → `Collection`
- `CollectionTaxonMap.taxon_tree` → `TaxonTree`
- `CollectionTaxonMap.taxon` → `Taxon` (root of the branch, or None)

## Filtering Behavior

When a site has `collection_taxon_map` entries for its collections, taxon queries are scoped to the mapped `taxon_tree_id`(s). If no mappings exist, all taxa are shown (no filter applied).

### Where filtering is applied

| Location                          | File                           | Description                                      |
|-----------------------------------|--------------------------------|--------------------------------------------------|
| Admin searchbar (taxa results)    | `app/blueprints/admin.py`     | Filters taxa autocomplete by site's tree_ids     |
| Admin taxa list (`/admin/taxa`)   | `app/blueprints/admin.py`     | `TaxaListAPI._apply_extra_filters`               |
| Frontend `/data` family dropdown  | `app/blueprints/frontpage.py` | Filters family options in search page             |
| Frontend `/taxa` index            | `app/blueprints/frontpage.py` | Filters family list on taxa browse page           |
| Taxon tree API (`/api/taxon-tree/trees`)    | `app/blueprints/frontpage.py` | Returns trees mapped to a collection    |
| Taxon tree API (`/api/taxon-tree/children`) | `app/blueprints/frontpage.py` | Resolves tree_id from collection's map  |

### Common filtering pattern

```python
collection_ids = [x.id for x in site.collections]  # or current_user.site.collection_ids
maps = CollectionTaxonMap.query.filter(
    CollectionTaxonMap.collection_id.in_(collection_ids)
).all()
if maps:
    tree_ids = list({m.taxon_tree_id for m in maps})
    query = query.filter(Taxon.tree_id.in_(tree_ids))
```

## Example Configuration

| collection_id | Collection | taxon_tree_id | Tree         | taxon_id | Meaning                   |
|---------------|-----------|---------------|--------------|----------|---------------------------|
| 1             | HAST      | 1             | HAST-legacy  | NULL     | HAST uses entire legacy tree |
| 8             | Fossil    | 2             | TaiCOL260224 | NULL     | Fossil uses entire TaiCOL tree |

Collections without mappings (e.g. HAST-藻類, HAST-真菌) inherit the filter from sibling collections on the same site. Since the site's `collection_ids` includes all collections, the query finds mappings from any collection in the site.
