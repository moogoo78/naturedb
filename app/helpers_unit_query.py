'''Unit-level query for /api/v1/units: list, facets and export share one filter.

Units are scoped by Unit.collection_id, not Record.collection_id: a unit may
sit in a different collection from its record (living plants in collection
'greenhouse' hang off herbarium records in collection 1). Collection-specific
fields are unit annotations, filtered and faceted by annotation_type id, so no
collection needs code of its own here.

filter (JSON object, keys AND-ed):
    collection_id   int | [int]          defaults to every collection of the site
    q               str                  space-separated tokens, each must match
    collector_id    [int]
    taxon_id        [int]                matches the taxa and all their descendants
    field_number    spec | [spec]        AND-ed; 'a--b' numeric range on
                                         Record.field_number_int, a number on
                                         field_number_int, other text exact
    locality        str                  tokens, each in locality_text(_en) or verbatim_locality
    notes           str                  tokens, each in Unit.notes
    catalog_number, disposition, kind_of_unit, basis_of_record, pub_status
                    value | [value] | {"not": [value]}
    annotations     {"<annotation_type_id>": value | [value] | {"not": [value]}}
    any             [filter, ...]        OR of sub-filters (same keys, AND-ed inside);
                                         their collection_id must be within the outer
                                         one, e.g. one collection whole + another
                                         limited to a taxon
'''
from sqlalchemy import (
    select,
    func,
    desc,
    or_,
    and_,
    exists,
)

from app.database import session
from app.models.collection import (
    Record,
    Unit,
    Person,
    AnnotationType,
    UnitAnnotation,
)
from app.models.taxon import TaxonRelation


class UnitQueryError(ValueError):
    pass


MATCH_FIELDS = {
    'catalog_number': Unit.catalog_number,
    'disposition': Unit.disposition,
    'kind_of_unit': Unit.kind_of_unit,
    'basis_of_record': Unit.basis_of_record,
    'pub_status': Unit.pub_status,
}

FACET_FIELDS = dict(MATCH_FIELDS, collector=Record.collector_id, taxon=Record.proxy_taxon_id,
                    collection=Unit.collection_id)

SORT_FIELDS = {
    # catalog/field numbers are strings: sort by length first so '9' < '10'
    'catalog_number': [func.length(Unit.catalog_number), Unit.catalog_number],
    'field_number': [Record.field_number_int, Record.field_number],
    'taxon': [Record.proxy_taxon_scientific_name],
    'collect_date': [Record.collect_date],
    'created': [Unit.created],
    'updated': [Unit.updated],
}

MAX_PAGE_SIZE = 500

EXPORT_COLUMNS = [
    ('unit_id', 'unit_id'),
    ('catalog_number', 'catalog_number'),
    ('field_number', 'field_number'),
    ('collector', 'collector'),
    ('collect_date', 'collect_date'),
    ('scientific_name', 'scientific_name'),
    ('common_name', 'common_name'),
    ('kind_of_unit', 'kind_of_unit'),
    ('disposition', 'disposition'),
    ('notes', 'notes'),
    ('record_id', 'record_id'),
]


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _match(col, value):
    if isinstance(value, dict):
        if 'not' not in value:
            raise UnitQueryError('a dict filter value takes the form {"not": [...]}')
        return or_(col.is_(None), col.not_in(_as_list(value['not'])))
    return col.in_(_as_list(value))


def _int_list(value, key):
    try:
        return [int(x) for x in _as_list(value)]
    except (TypeError, ValueError):
        raise UnitQueryError(f'{key} must be integers')


def resolve_collection_ids(filtr, allowed_ids):
    '''collection ids to query: the requested ones, which must all be allowed.'''
    if 'collection_id' not in filtr:
        return list(allowed_ids)
    ids = _int_list(filtr['collection_id'], 'collection_id')
    if not set(ids) <= set(allowed_ids):
        raise PermissionError('collection not in this site')
    return ids


def _q_token(token):
    if token.isdigit():
        return or_(Unit.catalog_number == token, Record.field_number == token)
    like = f'%{token}%'
    return or_(
        Unit.catalog_number.ilike(like),
        Record.field_number.ilike(like),
        Record.proxy_taxon_scientific_name.ilike(like),
        Record.proxy_taxon_common_name.ilike(like),
        Record.verbatim_collector.ilike(like),
        Person.full_name.ilike(like),
        Person.full_name_en.ilike(like),
        Unit.notes.ilike(like),
    )


def _field_number(spec):
    spec = str(spec).strip()
    parts = spec.split('--')
    if len(parts) == 2:
        try:
            return Record.field_number_int.between(int(parts[0]), int(parts[1]))
        except ValueError:
            raise UnitQueryError('field_number range takes numbers: "a--b"')
    if spec.isdigit():
        return Record.field_number_int == int(spec)
    if not spec:
        raise UnitQueryError('field_number is empty')
    return Record.field_number == spec  # e.g. '21299a'


MAX_ANY = 20


def unit_conditions(filtr, collection_ids):
    '''WHERE clauses for `filtr`; expects Record and Person joined as in base_select().'''
    conds = [Unit.collection_id.in_(collection_ids)]

    if 'any' in filtr:
        subs = filtr['any']
        if not isinstance(subs, list) or not subs or len(subs) > MAX_ANY \
                or not all(isinstance(x, dict) for x in subs):
            raise UnitQueryError(f'any takes a list of 1-{MAX_ANY} filter objects')
        conds.append(or_(*[
            and_(*unit_conditions(sub, resolve_collection_ids(sub, collection_ids)))
            for sub in subs
        ]))

    for token in (filtr.get('q') or '').split():
        conds.append(_q_token(token))

    if v := filtr.get('collector_id'):
        conds.append(Record.collector_id.in_(_int_list(v, 'collector_id')))

    if v := filtr.get('taxon_id'):
        ids = _int_list(v, 'taxon_id')
        descendants = select(TaxonRelation.child_id).where(TaxonRelation.parent_id.in_(ids))
        conds.append(or_(Record.proxy_taxon_id.in_(ids), Record.proxy_taxon_id.in_(descendants)))

    if v := filtr.get('field_number'):
        for spec in v if isinstance(v, list) else [v]:
            conds.append(_field_number(spec))

    for token in (filtr.get('locality') or '').split():
        like = f'%{token}%'
        conds.append(or_(
            Record.locality_text.ilike(like),
            Record.locality_text_en.ilike(like),
            Record.verbatim_locality.ilike(like),
        ))

    for token in (filtr.get('notes') or '').split():
        conds.append(Unit.notes.ilike(f'%{token}%'))

    for key, col in MATCH_FIELDS.items():
        if key in filtr and filtr[key] not in ('', None, []):
            conds.append(_match(col, filtr[key]))

    for type_id, value in (filtr.get('annotations') or {}).items():
        if value in ('', None, []):
            continue
        type_id = _int_list(type_id, 'annotations key')[0]
        if isinstance(value, dict):
            # units with no value for this type count as "not" any value
            has_value = exists().where(
                UnitAnnotation.unit_id == Unit.id,
                UnitAnnotation.annotation_type_id == type_id,
                UnitAnnotation.value.in_(_as_list(value.get('not', []))),
            )
            conds.append(~has_value)
        else:
            conds.append(exists().where(
                UnitAnnotation.unit_id == Unit.id,
                UnitAnnotation.annotation_type_id == type_id,
                UnitAnnotation.value.in_(_as_list(value)),
            ))

    return conds


def base_select(*columns):
    return select(*columns).select_from(Unit) \
        .join(Record, Unit.record_id == Record.id, isouter=True) \
        .join(Person, Record.collector_id == Person.id, isouter=True)


ROW_COLUMNS = (
    Unit.id,
    Unit.catalog_number,
    Unit.collection_id,
    Unit.kind_of_unit,
    Unit.basis_of_record,
    Unit.disposition,
    Unit.pub_status,
    Unit.notes,
    Unit.updated,
    Record.id.label('record_id'),
    Record.field_number,
    # text: Postgres accepts years past datetime.MAXYEAR and psycopg raises
    # while fetching them (see make_items_stmt)
    func.to_char(Record.collect_date, 'YYYY-MM-DD').label('collect_date'),
    Record.verbatim_collector,
    Record.proxy_taxon_id,
    Record.proxy_taxon_scientific_name,
    Record.proxy_taxon_common_name,
    Record.locality_text,
    Person.id.label('collector_id'),
    Person.full_name,
    Person.full_name_en,
)


def _order_by(sort):
    sort = sort or 'catalog_number'
    is_desc = sort.startswith('-')
    cols = SORT_FIELDS.get(sort.lstrip('-'))
    if cols is None:
        raise UnitQueryError(f'unknown sort: {sort}')
    cols = [desc(c).nulls_last() if is_desc else c.asc().nulls_last() for c in cols]
    return cols + [Unit.id]


def _annotations_by_unit(unit_ids):
    '''{unit_id: {annotation name: value}}; unit_ids is a list or a select of ids.'''
    out = {}
    if isinstance(unit_ids, list) and not unit_ids:
        return out
    rows = session.execute(
        select(UnitAnnotation.unit_id, AnnotationType.name, UnitAnnotation.value)
        .join(AnnotationType, AnnotationType.id == UnitAnnotation.annotation_type_id)
        .where(UnitAnnotation.unit_id.in_(unit_ids))
    ).all()
    for unit_id, name, value in rows:
        out.setdefault(unit_id, {})[name] = value
    return out


def _row_to_dict(r, annotations):
    return {
        'unit_id': r.id,
        'entity_key': f'u{r.id}',
        'catalog_number': r.catalog_number or '',
        'collection_id': r.collection_id,
        'kind_of_unit': r.kind_of_unit or '',
        'basis_of_record': r.basis_of_record or '',
        'disposition': r.disposition or '',
        'pub_status': r.pub_status or '',
        'notes': r.notes or '',
        'updated': r.updated.isoformat() if r.updated else '',
        'record_id': r.record_id,
        'field_number': r.field_number or '',
        'collect_date': r.collect_date or '',
        'collector': {
            'id': r.collector_id,
            'full_name': r.full_name or '',
            'full_name_en': r.full_name_en or '',
        } if r.collector_id else None,
        'verbatim_collector': r.verbatim_collector or '',
        'taxon': {
            'id': r.proxy_taxon_id,
            'scientific_name': r.proxy_taxon_scientific_name or '',
            'common_name': r.proxy_taxon_common_name or '',
        } if r.proxy_taxon_id else None,
        'locality_text': r.locality_text or '',
        'annotations': annotations.get(r.id, {}),
    }


def query_units(filtr, collection_ids, sort=None, start=0, end=50):
    start, end = int(start), int(end)
    if start < 0 or end <= start:
        raise UnitQueryError('range must be [start, end) with end > start >= 0')
    end = min(end, start + MAX_PAGE_SIZE)

    conds = unit_conditions(filtr, collection_ids)
    total = session.execute(base_select(func.count(Unit.id)).where(*conds)).scalar()
    rows = session.execute(
        base_select(*ROW_COLUMNS).where(*conds).order_by(*_order_by(sort)).offset(start).limit(end - start)
    ).all()
    annotations = _annotations_by_unit([r.id for r in rows])
    return {'data': [_row_to_dict(r, annotations) for r in rows], 'total': total, 'range': [start, start + len(rows)]}


def facet_units(filtr, collection_ids, fields, limit=100):
    '''Counts of units per value of each field, under the same filter.

    fields: names from FACET_FIELDS, or "annotation:<annotation_type_id>".
    A null value counts the units with no value.
    '''
    conds = unit_conditions(filtr, collection_ids)
    facets = {}
    for field in fields:
        if field.startswith('annotation:'):
            type_id = _int_list(field.split(':', 1)[1], 'annotation facet')[0]
            col = UnitAnnotation.value
            stmt = base_select(col, func.count(func.distinct(Unit.id))) \
                .join(UnitAnnotation, and_(UnitAnnotation.unit_id == Unit.id,
                                           UnitAnnotation.annotation_type_id == type_id), isouter=True)
            label_col = None
        elif field in FACET_FIELDS:
            col = FACET_FIELDS[field]
            label_col = {
                'collector': func.coalesce(func.max(Person.full_name), func.max(Person.full_name_en)),
                'taxon': func.max(Record.proxy_taxon_scientific_name),
            }.get(field)
            extra = [label_col] if label_col is not None else []
            stmt = base_select(col, func.count(func.distinct(Unit.id)), *extra)
        else:
            raise UnitQueryError(f'unknown facet field: {field}')

        rows = session.execute(
            stmt.where(*conds).group_by(col).order_by(desc(func.count(func.distinct(Unit.id))), col).limit(limit)
        ).all()
        facets[field] = [
            {'value': r[0], 'count': r[1], **({'label': r[2]} if label_col is not None else {})}
            for r in rows
        ]

    summary = session.execute(
        base_select(
            func.count(func.distinct(Unit.id)),
            func.count(func.distinct(Record.proxy_taxon_id)),
            func.count(func.distinct(Unit.id)).filter(Record.proxy_taxon_id.is_(None)),
        ).where(*conds)
    ).one()
    return {
        'facets': facets,
        'summary': {'units': summary[0], 'taxa': summary[1], 'units_without_taxon': summary[2]},
    }


def annotation_types(collection_ids, target='unit'):
    rows = AnnotationType.query.filter(
        AnnotationType.collection_id.in_(collection_ids),
        AnnotationType.target == target,
    ).order_by(AnnotationType.collection_id, AnnotationType.sort, AnnotationType.id).all()
    return [{
        'id': t.id,
        'collection_id': t.collection_id,
        'name': t.name,
        'label': t.label,
        'input_type': t.input_type,
        'options': (t.data or {}).get('options', []),
        'sort': t.sort,
    } for t in rows]


def export_rows(filtr, collection_ids, sort=None, max_rows=100000):
    '''(header, rows) for CSV/Excel: fixed unit columns + one column per unit annotation type.'''
    conds = unit_conditions(filtr, collection_ids)
    total = session.execute(base_select(func.count(Unit.id)).where(*conds)).scalar()
    if total > max_rows:
        raise UnitQueryError(f'{total} units match; narrow the filter to at most {max_rows}')

    types = annotation_types(collection_ids)
    type_names = list(dict.fromkeys(t['name'] for t in types))
    header = [label for _, label in EXPORT_COLUMNS] + type_names

    result = session.execute(base_select(*ROW_COLUMNS).where(*conds).order_by(*_order_by(sort))).all()
    annotations = _annotations_by_unit(base_select(Unit.id).where(*conds))
    rows = []
    for r in result:
        d = _row_to_dict(r, annotations)
        flat = {
            **d,
            'collector': (d['collector'] or {}).get('full_name') or (d['collector'] or {}).get('full_name_en') or d['verbatim_collector'],
            'scientific_name': (d['taxon'] or {}).get('scientific_name', ''),
            'common_name': (d['taxon'] or {}).get('common_name', ''),
        }
        rows.append([flat[key] for key, _ in EXPORT_COLUMNS] + [d['annotations'].get(n, '') for n in type_names])
    return header, rows
