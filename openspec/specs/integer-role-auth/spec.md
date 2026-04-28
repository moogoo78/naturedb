## ADDED Requirements

### Requirement: Integer role values
The User model SHALL define role as an Integer column with values 1-5 mapping to: 1=Root Administrator, 2=Collection Manager, 3=Collections Assistant, 4=Digitization Technician, 5=Students/Volunteer. The default value SHALL be 4.

#### Scenario: New user gets default role
- **WHEN** a new User is created without specifying a role
- **THEN** the role SHALL be 4 (Digitization Technician)

#### Scenario: Role values are valid integers
- **WHEN** querying any user in the database
- **THEN** the role value SHALL be an integer between 1 and 5

### Requirement: Named role constants
The User model SHALL define named constants: ROLE_ROOT=1, ROLE_MANAGER=2, ROLE_ASSISTANT=3, ROLE_TECHNICIAN=4, ROLE_VOLUNTEER=5. All role checks in application code SHALL use these constants instead of magic numbers.

#### Scenario: Code references use constants
- **WHEN** checking if user is a volunteer
- **THEN** the check SHALL be `current_user.role == User.ROLE_VOLUNTEER` (not `role == 5`)

### Requirement: Hierarchical role comparison
Authorization checks that gate on "admin-level access" SHALL use comparison operators (e.g., `role <= User.ROLE_MANAGER`) instead of equality checks against individual roles.

#### Scenario: Admin-only route
- **WHEN** a route requires admin access and user has role 3 (Collections Assistant)
- **THEN** access SHALL be denied because `3 > ROLE_MANAGER (2)`

#### Scenario: Manager access
- **WHEN** a route requires admin access and user has role 2 (Collection Manager)
- **THEN** access SHALL be granted because `2 <= ROLE_MANAGER (2)`

### Requirement: Volunteer-specific behavior
Routes that apply volunteer-specific restrictions SHALL check `role == User.ROLE_VOLUNTEER`. This includes: admin index redirect to volunteer tasks, auto-complete volunteer task on save, volunteer access control for unit editing.

#### Scenario: Volunteer redirect on admin index
- **WHEN** a user with role 5 (Volunteer) visits the admin index
- **THEN** they SHALL be redirected to volunteer_my_tasks

#### Scenario: Non-volunteer visits admin index
- **WHEN** a user with role 4 (Digitization Technician) visits the admin index
- **THEN** they SHALL see the normal admin dashboard

### Requirement: Data migration
An alembic migration SHALL convert all existing string role values to their integer equivalents (R→1, A→2, B→3, C→4, D→5) without data loss. The migration SHALL be reversible.

#### Scenario: Existing manager user
- **WHEN** migration runs and a user has role='A'
- **THEN** their role SHALL become 2

#### Scenario: Rollback migration
- **WHEN** the migration is downgraded
- **THEN** integer role 2 SHALL become 'A'
