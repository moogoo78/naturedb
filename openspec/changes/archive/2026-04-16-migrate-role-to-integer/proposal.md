## Why

The user role column is a single character string (`R`, `A`, `B`, `C`, `D`) with an implicit hierarchy. Permission checks are scattered string comparisons (`role == 'A'`, `role != 'A'`, `role == 'D'`). With integer roles, access control becomes range comparisons (`role <= 2` for admin access), making it easier to add new roles and reason about authorization.

## What Changes

- **BREAKING**: `user.role` column type changes from `String(4)` to `Integer`
- Role mapping: `R=1` (root admin), `A=2` (Collection Manager), `B=3` (Collections Assistant), `C=4` (Digitization Technician), `D=5` (Students/Volunteer)
- All role checks in Python code and Jinja templates updated to integer comparisons
- Alembic migration to alter column type and convert existing values
- Default role changes from `'C'` to `4`

## Capabilities

### New Capabilities
- `integer-role-auth`: Integer-based user role system with hierarchical comparison operators

### Modified Capabilities

## Impact

- **Model**: `app/models/site.py` — User.role column definition and default
- **Admin views**: `app/blueprints/admin.py` — 10+ role checks (volunteer redirect, task assignment, admin-only gates)
- **Templates**: `app/templates/admin/base.html` — sidebar/nav visibility, `app/templates/admin/unit-simple-entry.html` — admin-only UI sections
- **Migration**: New alembic version to ALTER COLUMN type and UPDATE existing values
- **Database**: All rows in `user` table will have role values converted
