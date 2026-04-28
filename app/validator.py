from datetime import date

from sqlalchemy import select, func, delete

from app.database import session
from app.models.collection import (
    AnnotationType,
    Identification,
    Record,
    RecordAnnotation,
    Unit,
    UnitAnnotation,
)

DATE_MIN = date(1700, 1, 1)


def validate_dates(collection_id) -> list[dict]:
    """
    Check Record.collect_date and Identification.date for out-of-range values:
      - before 1700-01-01
      - after today
    Returns list of dicts with keys: type, record_id, field, value, reason
    """
    issues = []
    today = date.today()

    stmt = select(Record.id, Record.collect_date).where(
        Record.collection_id == collection_id,
        Record.collect_date.isnot(None),
    ).where(
        (func.date(Record.collect_date) < DATE_MIN) |
        (func.date(Record.collect_date) > today)
    )
    for row in session.execute(stmt):
        reason = 'before 1700' if row.collect_date.date() < DATE_MIN else 'future date'
        issues.append({
            'type': 'record',
            'record_id': row.id,
            'field': 'collect_date',
            'value': str(row.collect_date.date()),
            'reason': reason,
        })

    stmt = (
        select(Identification.id, Identification.record_id, Identification.date)
        .join(Record, Identification.record_id == Record.id)
        .where(
            Record.collection_id == collection_id,
            Identification.date.isnot(None),
        )
        .where(
            (func.date(Identification.date) < DATE_MIN) |
            (func.date(Identification.date) > today)
        )
    )
    for row in session.execute(stmt):
        reason = 'before 1700' if row.date.date() < DATE_MIN else 'future date'
        issues.append({
            'type': 'identification',
            'record_id': row.record_id,
            'id': row.id,
            'field': 'date',
            'value': str(row.date.date()),
            'reason': reason,
        })

    return issues


def validate_catalog_numbers(collection_id) -> list[dict]:
    """
    Check Unit.catalog_number for duplicates within the collection.
    Returns list of dicts with keys: field, value, unit_ids, count
    """
    stmt = (
        select(
            Unit.catalog_number,
            func.array_agg(Unit.id).label('unit_ids'),
            func.count(Unit.id).label('cnt'),
        )
        .where(
            Unit.collection_id == collection_id,
            Unit.catalog_number.isnot(None),
            Unit.catalog_number != '',
        )
        .group_by(Unit.catalog_number)
        .having(func.count(Unit.id) > 1)
    )
    issues = []
    for row in session.execute(stmt):
        issues.append({
            'field': 'catalog_number',
            'value': row.catalog_number,
            'unit_ids': sorted(row.unit_ids),
            'count': row.cnt,
        })
    return issues


def _get_or_create_annotation_type(name, label, target, collection_id):
    at = session.execute(
        select(AnnotationType).where(
            AnnotationType.name == name,
            AnnotationType.collection_id == collection_id,
        )
    ).scalar_one_or_none()
    if at is None:
        at = AnnotationType(
            name=name,
            label=label,
            target=target,
            input_type='input',
            collection_id=collection_id,
        )
        session.add(at)
        session.flush()
    return at


def clear_tags(collection_id):
    """Remove all validator-written annotations for a collection."""
    record_ids = select(Record.id).where(Record.collection_id == collection_id).scalar_subquery()
    unit_ids = select(Unit.id).where(Unit.collection_id == collection_id).scalar_subquery()

    at_names = ('date_issue', 'catalog_number_issue')
    at_ids = select(AnnotationType.id).where(
        AnnotationType.name.in_(at_names),
        AnnotationType.collection_id == collection_id,
    ).scalar_subquery()

    session.execute(
        delete(RecordAnnotation).where(
            RecordAnnotation.record_id.in_(record_ids),
            RecordAnnotation.annotation_type_id.in_(at_ids),
        )
    )
    session.execute(
        delete(UnitAnnotation).where(
            UnitAnnotation.unit_id.in_(unit_ids),
            UnitAnnotation.annotation_type_id.in_(at_ids),
        )
    )
    session.commit()


def tag_issues(collection_id, clear=False):
    """Write RecordAnnotation / UnitAnnotation rows for detected issues."""
    if clear:
        clear_tags(collection_id)

    date_at = _get_or_create_annotation_type(
        name='date_issue',
        label='日期問題',
        target='record',
        collection_id=collection_id,
    )
    accn_at = _get_or_create_annotation_type(
        name='catalog_number_issue',
        label='館號重複',
        target='unit',
        collection_id=collection_id,
    )

    date_issues = validate_dates(collection_id)
    accn_issues = validate_catalog_numbers(collection_id)

    for issue in date_issues:
        session.add(RecordAnnotation(
            record_id=issue['record_id'],
            annotation_type_id=date_at.id,
            value=f"{issue['field']}: {issue['value']} ({issue['reason']})",
        ))

    for issue in accn_issues:
        for unit_id in issue['unit_ids']:
            session.add(UnitAnnotation(
                unit_id=unit_id,
                annotation_type_id=accn_at.id,
                value=issue['value'],
            ))

    session.commit()
    return date_issues, accn_issues
