# User Collection Scope

## Purpose

A user's role decides **what** they may do; collection scope decides **which data** it applies to. Before this, every user saw and edited all collections of their site. Now a user can be limited to some of them, e.g. a greenhouse editor who works on collection 9 (溫室標本) but cannot touch HAST (collection 1) on the same site.

## Data Model

```
user_collection
  user_id          FK -> user        ON DELETE CASCADE
  collection_id    FK -> collection  ON DELETE CASCADE
  PK (user_id, collection_id)
```

`User.collection_ids` (`app/models/site.py`) is the single source of truth:

- assigned rows -> those collections (sorted by `collection.sort`)
- no rows -> every collection of the user's site, i.e. the old behavior

Existing users have no rows, so nothing changes for them.

### Examples

| user | user_collection | sees / edits |
|---|---|---|
| greenhouse editor | 9 | greenhouse only |
| HAST + greenhouse | 1, 9 | both |
| everyone else | (none) | whole site |

## Rules

- Role checks are unchanged: a Cataloger limited to collection 9 is still a Cataloger, just within collection 9.
- Per-user reads and writes in the admin blueprint and `/api/v1` use `current_user.collection_ids`, not `site.collection_ids`.
- Endpoints that act on one record, unit, media object or collection call `ensure_collection_access(collection_id)` (`app/blueprints/admin.py`), which aborts 403 for anonymous users or collections outside the scope. **New endpoints must do the same.**
- Records follow their **units**, not `record.collection_id`. A record's collections are its units' collections (a unit without one counts as the record's). A user may **view** a record if any of them is in scope and **edit** it only if all are. On prod every greenhouse unit (collection 9) sits on a collection-1 record, and 525 of those records also carry HAST units: those are read-only for a greenhouse-only user, so they cannot change HAST's collecting data. The record form then shows a notice instead of the unlock button. Helpers: `can_view_record` / `can_edit_record` / `ensure_record_access` in `admin.py`.
- Catalog number uniqueness stays site-wide: it is a data rule, not a permission.
- Public pages (`frontpage.py`, public `api.py`) still scope by the site; collection scope is for logged-in users only.

### Guarded endpoints

| Endpoint | Outside scope |
|---|---|
| `GET /admin/api/records/<id>` | 403 unless a unit is in scope |
| `PATCH/DELETE /admin/api/records/<id>` | 403 unless every unit is in scope |
| `POST /admin/api/records/` (create, by `collection_id`) | 403 |
| `/admin/records/create?collection_id=` | 403 |
| `/admin/records/<key>` | 404; read-only when shared |
| `/admin/units/<id>/simple-entry` | 404 |
| `/admin/api/units/<id>/media*` | 403 |
| `/admin/api/units/<id>/simple-edit` | 403 (also when its record is shared) |
| `/admin/api/quick-edit` | JSON `message: error`, nothing saved (also when its record is shared) |
| `/admin/api/collections/<id>/options`, `/tracking-tags` | 403 |
| `/api/v1/units*`, `/api/v1/collections/<id>/annotation-types` | 403 |
| `/api/v1/me` | lists only the user's collections |

## Usage

Create a scoped user (`--collection` is repeatable; a collection outside the site is rejected):

```bash
docker compose exec flask flask createuser <username> <passwd> <site_id> <role> --collection 9
```

Change an existing user (no admin UI yet):

```sql
INSERT INTO user_collection (user_id, collection_id) VALUES (<user_id>, 9);
-- back to whole site
DELETE FROM user_collection WHERE user_id = <user_id>;
```

## Deploy

- Migration `d6e8f0a2b4c5_user_collection`. `main.yml` (prod) and `devel.yml` (staging, manual trigger only) both run it on deploy.
- Tests: `tests/test_collection_scope.py`.
