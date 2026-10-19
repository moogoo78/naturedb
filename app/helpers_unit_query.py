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
    case,
    literal,
)

from flask import url_for

from app.database import session
from app.models.collection import (
    Collection,
    Record,
    Unit,
    Person,
    AnnotationType,
    MultimediaObject,
    UnitAnnotation,
)
from app.models.site import Organization
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
    # catalog/field numbers are strings: sort by length first so '9' < '10';
    # blank ones count as null, so they come last either way
    'catalog_number': [func.length(func.nullif(Unit.catalog_number, '')), func.nullif(Unit.catalog_number, '')],
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
    Unit.cover_image_id,
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


def _sort_fields(sort):
    sort = sort or 'catalog_number'
    cols = SORT_FIELDS.get(sort.lstrip('-'))
    if cols is None:
        raise UnitQueryError(f'unknown sort: {sort}')
    return cols, sort.startswith('-')


def _order_by(sort):
    cols, is_desc = _sort_fields(sort)
    cols = [desc(c).nulls_last() if is_desc else c.asc().nulls_last() for c in cols]
    return cols + [Unit.id]


def _page(start, end):
    start, end = int(start), int(end)
    if start < 0 or end <= start:
        raise UnitQueryError('range must be [start, end) with end > start >= 0')
    return start, min(end, start + MAX_PAGE_SIZE)


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


def _cover_image_urls(image_ids):
    '''{multimedia_object id: file_url} for one page of rows.'''
    ids = {i for i in image_ids if i}
    if not ids:
        return {}
    rows = session.execute(
        select(MultimediaObject.id, MultimediaObject.file_url).where(MultimediaObject.id.in_(ids))
    ).all()
    return {i: url for i, url in rows if url}


def _catalog_key(value):
    '''catalog number as the public page matches it (helpers._catalog_number_match):
    leading zeros dropped from an all-digit value that has a nonzero digit'''
    stripped = value.lstrip('0')
    return stripped if value.isdigit() and stripped else value


# the same, in SQL
CATALOG_KEY = case(
    (and_(Unit.catalog_number.op('~')('^[0-9]+$'), func.ltrim(Unit.catalog_number, '0') != ''),
     func.ltrim(Unit.catalog_number, '0')),
    else_=Unit.catalog_number)


def _key_owners(site, by_org, keys):
    '''{(org_code or None, catalog key): number of published units of the site
    the public page would match}: it picks the first of them, so a key is only
    a link when the number is 1'''
    org = Organization.code if by_org else literal(None)
    stmt = (select(org, CATALOG_KEY, func.count())
            .select_from(Unit).join(Collection, Collection.id == Unit.collection_id)
            .outerjoin(Organization, Organization.id == Collection.organization_id)
            .where(Unit.pub_status == 'P', Unit.collection_id.in_(site.collection_ids),
                   CATALOG_KEY.in_({k for _, k in keys}))
            .group_by(org, CATALOG_KEY))
    return {(o, k): n for o, k, n in session.execute(stmt)}


def _detail_paths(rows):
    '''{unit_id: path of its public specimen page} for one page of rows.

    Only published units (pub_status P) have one: the public page 404s the
    others. The key comes from the collection's site setting
    frontend.specimens.url, as Unit.get_link builds it; without the setting it
    is COLLECTION:catalog_number. A blank catalog number, an {org_code}
    template on a collection without an organization code, or a template with
    other placeholders gives no path.

    Nor does a key the page cannot resolve to this unit: it looks up the
    catalog number among the site's published units (within the org for an
    {org_code} key, the whole site otherwise) and takes the first match, so a
    catalog number shared by two of them, e.g. a living plant numbered like a
    herbarium sheet of the same organization, would link to the wrong one.'''
    rows = [r for r in rows if r.pub_status == 'P' and (r.catalog_number or '').strip()]
    if not rows:
        return {}
    collections = {c.id: c for c in Collection.query.filter(Collection.id.in_({r.collection_id for r in rows}))}
    candidates = {}  # (site, by_org) -> [(unit id, path, (org_code, catalog key))]
    out = {}
    for r in rows:
        c = collections.get(r.collection_id)
        if not c:
            continue
        template = c.site.get_settings('frontend.specimens.url') if c.site else None
        org_code = c.organization.code if c.organization else ''
        if template and '{org_code}' in template and not org_code:
            continue
        try:
            key = Unit.specimen_record_key(template or f'{c.name.upper()}:{{catalog_number}}',
                                           org_code, r.catalog_number, r.id)
        except (KeyError, IndexError, ValueError):
            continue
        path = url_for('frontpage.specimen_detail', record_key=key)
        if template and '{catalog_number}' not in template:
            out[r.id] = path  # keyed by unit id: unique
        elif c.site:
            by_org = bool(template) and '{org_code}' in template
            candidates.setdefault((c.site, by_org), []).append(
                (r.id, path, (org_code if by_org else None, _catalog_key(r.catalog_number))))
    for (site, by_org), items in candidates.items():
        owners = _key_owners(site, by_org, [k for _, _, k in items])
        out.update({uid: path for uid, path, k in items if owners.get(k) == 1})
    return out


def _row_to_dict(r, annotations, images=None, details=None):
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
        # stored URL as is; size variants are a storage convention of the client's
        'cover_image_url': (images or {}).get(r.cover_image_id, ''),
        # path on naturedb's public site; '' when the unit is not published
        'detail_path': (details or {}).get(r.id, ''),
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
    start, end = _page(start, end)

    conds = unit_conditions(filtr, collection_ids)
    total = session.execute(base_select(func.count(Unit.id)).where(*conds)).scalar()
    rows = session.execute(
        base_select(*ROW_COLUMNS).where(*conds).order_by(*_order_by(sort)).offset(start).limit(end - start)
    ).all()
    annotations = _annotations_by_unit([r.id for r in rows])
    images = _cover_image_urls([r.cover_image_id for r in rows])
    details = _detail_paths(rows)
    return {'data': [_row_to_dict(r, annotations, images, details) for r in rows], 'total': total, 'range': [start, start + len(rows)]}


# a unit without a record is a group of its own
GROUP_KEY = func.coalesce(Unit.record_id, -Unit.id)
RECORD_FIELDS = ('record_id', 'field_number', 'collect_date', 'collector', 'verbatim_collector',
                 'taxon', 'locality_text')


def query_records(filtr, collection_ids, sort=None, start=0, end=50):
    '''The matching units grouped by record: a page of records, each with its
    matching units (not the record's other units). Same filter as query_units;
    records sort by the min (asc) / max (desc) of the sort field over their units.'''
    start, end = _page(start, end)
    conds = unit_conditions(filtr, collection_ids)
    total = session.execute(base_select(func.count(func.distinct(GROUP_KEY))).where(*conds)).scalar()

    cols, is_desc = _sort_fields(sort)
    order = [desc(func.max(c)).nulls_last() if is_desc else func.min(c).asc().nulls_last() for c in cols]
    keys = session.execute(
        base_select(GROUP_KEY).where(*conds).group_by(GROUP_KEY)
        .order_by(*order, GROUP_KEY).offset(start).limit(end - start)
    ).scalars().all()

    rows = session.execute(
        base_select(*ROW_COLUMNS, GROUP_KEY.label('group_key'))
        .where(*conds, GROUP_KEY.in_(keys)).order_by(*_order_by('catalog_number'))
    ).all() if keys else []
    annotations = _annotations_by_unit([r.id for r in rows])
    images = _cover_image_urls([r.cover_image_id for r in rows])
    details = _detail_paths(rows)
    units = {}
    for r in rows:
        units.setdefault(r.group_key, []).append(_row_to_dict(r, annotations, images, details))

    data = []
    for key in keys:
        group = units[key]
        first = group[0]
        data.append({
            'entity_key': f'r{first["record_id"]}' if first['record_id'] else first['entity_key'],
            **{k: first[k] for k in RECORD_FIELDS},
            'units': group,
        })
    return {'data': data, 'total': total, 'range': [start, start + len(data)]}


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
