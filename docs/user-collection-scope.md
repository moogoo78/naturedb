# User Collection Scope

## Purpose

A user's role decides **what** they may do; collection scope decides **which data** it applies to, and whether they may only view it or also edit it. Before this, every user saw and edited all collections of their site. Now a user can be limited to some of them, e.g. the greenhouse editor: edits collection 9 (溫室標本), only views HAST (collection 1).

The greenhouse editor needs to *see* collection 1 for two reasons: every greenhouse unit sits on a collection-1 record (so the record form loads collection 1's options), and the greenhouse client searches HAST's Begoniaceae as a second source.

## Data Model

```
user_collection
  user_id          FK -> user        ON DELETE CASCADE
  collection_id    FK -> collection  ON DELETE CASCADE
  can_edit         boolean NOT NULL DEFAULT true   (false = view only)
  PK (user_id, collection_id)
```

`User` (`app/models/site.py`) is the single source of truth:

- `collection_ids`: collections the user may **view** — every assigned row
- `editable_collection_ids`: collections the user may **edit** — rows with `can_edit`
- no rows -> both are every collection of the user's site, i.e. the old behavior

Existing users have no rows, so nothing changes for them.

### Examples

| user | user_collection | views | edits |
|---|---|---|---|
| greenhouse editor | 9 (edit), 1 (view) | greenhouse + HAST | greenhouse |
| greenhouse only | 9 (edit) | greenhouse | greenhouse |
| everyone else | (none) | whole site | whole site |

## Rules

- Role checks are unchanged: a Cataloger limited to collection 9 is still a Cataloger, just within collection 9.
- Lists and searches in the admin blueprint and `/api/v1` use `current_user.collection_ids` (view), not `site.collection_ids`.
- Endpoints that act on one record, unit, media object or collection call `ensure_collection_access(collection_id, edit=...)` (`app/blueprints/admin.py`), which aborts 403 for anonymous users or collections outside the scope: `edit=True` for anything that writes, view for metadata reads (options, tracking tags). **New endpoints must do the same.**
- Records follow their **units**, not `record.collection_id`. A record's collections are its units' collections (a unit without one counts as the record's). A user may **view** a record if any of them is viewable and **edit** it only if all are editable. On prod 525 greenhouse records also carry HAST units: those are read-only for the greenhouse editor, so they cannot change HAST's collecting data. The record form then shows a notice instead of the unlock button. Helpers: `can_view_record` / `can_edit_record` / `ensure_record_access` in `admin.py`.
- A unit added to a record goes to the record's collection, unless the user may not edit it: then to an editable collection the record's units already use, else the user's first editable one (`new_unit_collection_id` in `admin.py`, passed to `put_entity` as `unit_collection_id`). So a greenhouse unit added (or branched) on a collection-1 record lands in collection 9. Unrestricted users are unaffected: they can edit the record's collection, so new units still go there.
- Unit annotation/assertion types of the record form are still the **record** collection's.
- Catalog number uniqueness stays site-wide: it is a data rule, not a permission.
- Public pages (`frontpage.py`, public `api.py`) still scope by the site; collection scope is for logged-in users only.

### Guarded endpoints

| Endpoint | Needs |
|---|---|
| `GET /admin/api/records/<id>` | view (any unit) |
| `PATCH/DELETE /admin/api/records/<id>` | edit (every unit) |
| `POST /admin/api/records/` (create, by `collection_id`) | edit |
| `/admin/records/create?collection_id=` | edit |
| `/admin/records/<key>` | view (404 otherwise); read-only without edit |
| `/admin/units/<id>/simple-entry` | view (404 otherwise) |
| `/admin/api/units/<id>/media*` | edit |
| `/admin/api/units/<id>/simple-edit` | edit, unit and record |
| `/admin/api/quick-edit` | edit, unit and record (JSON `message: error` otherwise, nothing saved) |
| `/admin/api/collections/<id>/options`, `/tracking-tags` | view |
| `/api/v1/units*`, `/api/v1/collections/<id>/annotation-types` | view |
| `/api/v1/me` | lists viewable collections, each with `can_edit` |

## Usage

Create a scoped user (`--collection` = editable, `--view-collection` = view only; both repeatable; a collection outside the site is rejected):

```bash
docker compose exec flask flask createuser <username> <passwd> <site_id> <role> --collection 9 --view-collection 1
```

Change an existing user (no admin UI yet):

```sql
INSERT INTO user_collection (user_id, collection_id, can_edit) VALUES (<user_id>, 1, false);
UPDATE user_collection SET can_edit = true WHERE user_id = <user_id> AND collection_id = 1;
-- back to whole site
DELETE FROM user_collection WHERE user_id = <user_id>;
```

## Deploy

- Migrations `d6e8f0a2b4c5_user_collection`, `e7f9a1b3c5d6_user_collection_can_edit`. `main.yml` (prod) and `devel.yml` (staging, manual trigger only) both run them on deploy.
- Tests: `tests/test_collection_scope.py`.
