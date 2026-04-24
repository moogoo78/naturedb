## 1. Model & Constants

- [x] 1.1 Add ROLE_ROOT, ROLE_MANAGER, ROLE_ASSISTANT, ROLE_TECHNICIAN, ROLE_VOLUNTEER constants to User model in `app/models/site.py`
- [x] 1.2 Change User.role column from `String(4)` to `Integer` with `default=4`
- [x] 1.3 Update role comment to document integer mapping

## 2. Alembic Migration

- [x] 2.1 Create alembic migration: add temp `role_int` column, populate via CASE (R→1, A→2, B→3, C→4, D→5), drop old `role`, rename `role_int` to `role`, set default=4
- [x] 2.2 Write downgrade function: reverse mapping (1→R, 2→A, 3→B, 4→C, 5→D)

## 3. Admin Views

- [x] 3.1 Update `app/blueprints/admin.py` line 209: volunteer redirect `role == 'D'` → `role == User.ROLE_VOLUNTEER`
- [x] 3.2 Update `app/blueprints/admin.py` line 569: auto-complete volunteer task `role == 'D'` → `role == User.ROLE_VOLUNTEER`
- [x] 3.3 Update `app/blueprints/admin.py` line 1357: volunteer access control `role == 'D'` → `role == User.ROLE_VOLUNTEER`
- [x] 3.4 Update `app/blueprints/admin.py` line 1382, 1458, 1544, 1571: admin-only gates `role != 'A'` → `role > User.ROLE_MANAGER`
- [x] 3.5 Update `app/blueprints/admin.py` line 1389: volunteer query `User.role == 'D'` → `User.role == User.ROLE_VOLUNTEER`

## 4. Templates

- [x] 4.1 Update `app/templates/admin/base.html` line 15: volunteer layout `role == "D"` → `role == 5`
- [x] 4.2 Update `app/templates/admin/base.html` line 60, 103: manager nav `role == "A"` → `role <= 2`
- [x] 4.3 Update `app/templates/admin/unit-simple-entry.html` lines 1273, 1285, 1299: admin-only sections `role == "A"` → `role <= 2`

## 5. Verification

- [x] 5.1 Run migration on dev database and verify role values converted correctly
- [x] 5.2 Test admin index as volunteer (role=5) — should redirect to volunteer tasks
- [x] 5.3 Test admin index as manager (role=2) — should show dashboard
- [x] 5.4 Test admin-only routes as non-admin — should be denied
