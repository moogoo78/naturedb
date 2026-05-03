# Changelog

## User Role Consolidation & Renaming — 2026-05-01

### Application Changes

- **Consolidated user roles** — Merged `ROLE_TECHNICIAN` (4) and `ROLE_INTERN` (5) into single `ROLE_CATALOGER` (4)
- **Promoted volunteer role** — `ROLE_VOLUNTEER` now has role id 5 (previously 6)
- **Renamed all roles** for natural history collection context:
  - `ROLE_ROOT` → **System Administrator**
  - `ROLE_MANAGER` → **Site Manager**
  - `ROLE_ASSISTANT` → **Collection Curator**
  - `ROLE_CATALOGER` → **Cataloger**
  - `ROLE_VOLUNTEER` → **Annotator**
- Updated role hierarchy in `User` model to 5 levels

### Rationale

- Technician and Intern roles had identical permissions and overlapping responsibilities
- Consolidation simplifies role management for natural history collection systems
- New names better reflect actual responsibilities in museum collection workflows:
  - "System Administrator" for root access
  - "Site Manager" for site-level operations
  - "Collection Curator" for collection-level management
  - "Cataloger" for data entry specialists
  - "Annotator" for community contributors

### Notes

- No code references to removed `ROLE_TECHNICIAN` or `ROLE_INTERN` constants found
- Data reset handled manually

## 人名相關 — 2026-03-03

### Schema Changes

- **New columns on `person`** — `given_name`, `inherited_name`, `given_name_en`, `inherited_name_en`, `preferred_name` (migrating off `atomized_name` JSONB)
- **New table `person_group`** — named groups for organizing person lists (id, name, created, updated)
- **New table `person_group_map`** — many-to-many linking persons to groups (person_id, group_id)
- **Dropped table `collection_person_map`** — replaced by person_group_map
- **Dropped column `person.site_id`** — person-to-site ownership superseded by group membership

### Application

- `Person.display_name` now reads from new name columns instead of `atomized_name` JSONB
- `RecordPerson` relationships wired up — companions (co-collectors) stored as Person references, falling back to legacy text fields
- `PersonGroup` model added with bidirectional `people`/`groups` relationships
- Person dropdown in admin record form now filters by `admin.person_group_id` site setting (falls back to all persons)
- Removed dead `list_collection_filter` config from admin_register

### Data

- 3 person groups created: **herbarium** (id=1), **fossil** (id=2), **HAST-alga** (id=3)
- 1342 existing persons mapped to herbarium group

### Migrations

1. `5a005bedbbbc` — add person atomized name columns
2. `f5ecbe5589ed` — add person.site_id (later dropped)
3. `a1b2c3d4e5f6` — create person_group + person_group_map
4. `b2c3d4e5f6a7` — drop collection_person_map
5. `c3d4e5f6a7b8` — drop person.site_id
