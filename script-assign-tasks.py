"""Batch assign volunteer tasks by unit ID range (descending).

Usage:
    # inside docker container:
    cd /code && python script-assign-tasks.py <user_id> <collection_id> <unit_id_start> <num_of_tasks> [--assigned-by <admin_user_id>]

    # from host:
    docker compose exec flask bash -c "cd /code && python script-assign-tasks.py 3 1 200 10 --assigned-by 1"

Assigns NUM_OF_TASKS units to USER_ID, starting from UNIT_ID_START
and going downward (200, 199, 198, ...). Only units belonging to
COLLECTION_ID are assigned. Units that already have a task are skipped.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description='Assign volunteer tasks by unit ID range (descending)')
    parser.add_argument('user_id', type=int, help='Volunteer user ID')
    parser.add_argument('collection_id', type=int, help='Collection ID')
    parser.add_argument('unit_id_start', type=int, help='Starting unit ID (descending)')
    parser.add_argument('num_of_tasks', type=int, help='Number of tasks to assign')
    parser.add_argument('--assigned-by', type=int, default=None, help='Admin user ID who assigns the tasks')
    parser.add_argument('--dry-run', action='store_true', help='Preview without committing')
    args = parser.parse_args()

    from app.database import session
    from app.models.collection import Unit, VolunteerTask
    from app.models.site import User

    # Validate user
    user = User.query.get(args.user_id)
    if not user:
        print(f'Error: user {args.user_id} not found')
        sys.exit(1)

    # Validate assigned_by
    assigned_by = None
    if args.assigned_by:
        assigned_by = User.query.get(args.assigned_by)
        if not assigned_by:
            print(f'Error: assigned_by user {args.assigned_by} not found')
            sys.exit(1)

    # Fetch candidate units: collection match, id <= start, ordered desc
    candidates = (
        Unit.query
        .filter(
            Unit.collection_id == args.collection_id,
            Unit.id <= args.unit_id_start,
        )
        .order_by(Unit.id.desc())
        .limit(args.num_of_tasks * 2)  # fetch extra in case some already assigned
        .all()
    )

    if not candidates:
        print(f'No units found in collection {args.collection_id} with id <= {args.unit_id_start}')
        sys.exit(1)

    assigned = 0
    skipped = 0
    for unit in candidates:
        if assigned >= args.num_of_tasks:
            break
        existing = VolunteerTask.query.filter(VolunteerTask.unit_id == unit.id).first()
        if existing:
            skipped += 1
            continue

        task = VolunteerTask(
            unit_id=unit.id,
            volunteer_id=args.user_id,
            assigned_by_id=args.assigned_by,
            status='assigned',
        )
        session.add(task)
        assigned += 1
        prefix = '[dry-run] ' if args.dry_run else ''
        print(f'  {prefix}assigned unit {unit.id} (accession: {unit.accession_number})')

    if assigned > 0 and not args.dry_run:
        session.commit()

    print(f'\nDone: {assigned} assigned, {skipped} skipped (already have tasks)')
    print(f'Volunteer: {user.username} (id={args.user_id})')
    if assigned_by:
        print(f'Assigned by: {assigned_by.username} (id={args.assigned_by})')
    print(f'Collection: {args.collection_id}, start: {args.unit_id_start}, requested: {args.num_of_tasks}')
    if args.dry_run:
        print('(dry-run mode, nothing committed)')


if __name__ == '__main__':
    main()
