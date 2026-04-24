## Context

User roles are stored as single-character strings with an implicit hierarchy: R > A > B > C > D. Authorization checks are equality comparisons scattered across admin views and templates. Adding roles or checking "at least this level" requires listing multiple string values. The codebase just went through a role rename (B→D for volunteers), highlighting the fragility of string-based roles.

## Goals / Non-Goals

**Goals:**
- Replace string role column with integer for hierarchical comparisons
- Simplify authorization: `role <= ROLE_MANAGER` instead of `role == 'A'`
- Define named constants for roles to avoid magic numbers
- Migrate existing data in a single alembic migration

**Non-Goals:**
- Full RBAC or permission system — this is a column type change, not an authorization framework
- Changing what each role can do — behavior stays identical
- Adding new roles — just converting the existing five

## Decisions

### Role integer mapping

| Integer | Old String | Name |
|---------|-----------|------|
| 1 | R | Root Administrator |
| 2 | A | Collection Manager |
| 3 | B | Collections Assistant |
| 4 | C | Digitization Technician |
| 5 | D | Students/Volunteer |

Lower number = higher privilege. This means `role <= 2` = admin-level access.

**Why ascending integers**: Natural ordering where 1 is most privileged. Matches common patterns (Unix UID 0 = root). Using 1-based instead of 0-based keeps it intuitive for non-developers who may see the database.

### Named constants on the User model

```python
class User(Base):
    ROLE_ROOT = 1
    ROLE_MANAGER = 2
    ROLE_ASSISTANT = 3
    ROLE_TECHNICIAN = 4
    ROLE_VOLUNTEER = 5
```

Code uses constants: `current_user.role <= User.ROLE_MANAGER` instead of magic numbers.

### Migration strategy

Single alembic migration that:
1. Adds a temporary integer column `role_int`
2. Populates it via CASE expression from current string values
3. Drops old `role` column
4. Renames `role_int` to `role`
5. Sets default to 4 (Digitization Technician)

**Why not ALTER TYPE directly**: PostgreSQL can't cast arbitrary strings to integers. A temp column approach is cleaner and has a clear rollback path.

## Risks / Trade-offs

- **Data loss if mapping is wrong** → Migration uses explicit CASE mapping with no fallback NULL; unmapped values raise an error. Test on dev database first.
- **Downtime during migration** → The migration is fast (UPDATE + column rename on a small table). No downtime expected.
- **Rollback** → Downgrade function reverses the mapping (integer → string). Fully reversible.
