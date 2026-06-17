'''
Public, cross-origin specimen API served from the `api.{domain}` subdomain.

Canonical path is `/v1/specimens` (registered with url_prefix='/v1' in
application.py); there is no `/api` segment because the subdomain already
namespaces it. All data exposed here is public (`pub_status='P'`), so the
`site` scope is an optional convenience filter, not an authorization boundary.

Every returned row is a physical specimen: the query joins Unit -> Record and
requires a non-empty catalog_number, hence the resource name `specimens`.

The legacy `{host}/api/v1/search` endpoint (app/blueprints/api.py) is left
untouched for back-compat. Both reuse `make_specimen_query` and
`serialize_specimen_row` so the record shape stays identical.
'''
import json
import time

from flask import (
    Blueprint,
    request,
    jsonify,
    abort,
)
from sqlalchemy import select, func, desc

from app.database import session
from app.models.site import Site
from app.models.collection import Record, Person, Unit
from app.helpers_query import (
    make_specimen_query,
    serialize_specimen_row,
)

specimens_api = Blueprint('specimens_api', __name__)

# All public data → open CORS for read-only GETs. See conversation rationale:
# locking CORS on a fully public API buys nothing and breaks third-party
# consumers (cf. GBIF, iNaturalist).
@specimens_api.after_request
def add_cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp


def _resolve_scope(site_name):
    '''Resolve (collection_ids, custom_area_class_ids) for an optional site slug.

    No site  -> all collections (cross-site public search).
    Known    -> that site's collections + its custom area classes.
    Unknown  -> 400 (a typo, not an auth failure — all data is public anyway).
    '''
    if not site_name:
        collection_ids = [x[0] for x in session.execute(select(Record.collection_id).distinct()).all()]
        return collection_ids, []

    site = session.execute(select(Site).where(Site.name == site_name)).scalar()
    if site is None:
        abort(400, description=f'unknown site: {site_name}')

    custom_area_class_ids = [x.id for x in site.get_custom_area_classes()]
    return site.collection_ids, custom_area_class_ids


@specimens_api.route('/specimens', methods=['GET'])
def get_specimens():
    site_name = request.args.get('site', '')
    total = request.args.get('total', None)

    # Client-supplied JSON — malformed input is a client error (400), not a 500.
    try:
        filtr = json.loads(request.args.get('filter')) if request.args.get('filter') else {}
        sort = json.loads(request.args.get('sort')) if request.args.get('sort') else []
        rng = json.loads(request.args.get('range')) if request.args.get('range') else [0, 20]
    except (ValueError, TypeError) as e:
        abort(400, description=f'invalid JSON in filter/sort/range: {e}')

    # `q` convenience param folds into the filter dict consumed by the query builder.
    if q := request.args.get('q'):
        filtr.setdefault('q', q)

    collection_ids, custom_area_class_ids = _resolve_scope(site_name)
    auth = {'collection_id': collection_ids, 'role': '', 'area-class-id': []}

    stmt = make_specimen_query(filtr, auth)
    base_stmt = stmt

    # sort
    if sort:
        for s in sort:
            if s in ('field_number', '-field_number', 'collector', '-collector'):
                col = desc(Record.field_number_int) if s.startswith('-') else Record.field_number_int
                stmt = stmt.order_by(Person.sorting_name, col)
            elif s in ('catalog_number', '-catalog_number'):
                if s.startswith('-'):
                    stmt = stmt.order_by(desc(func.length(Unit.catalog_number)), desc(Unit.catalog_number))
                else:
                    stmt = stmt.order_by(func.length(Unit.catalog_number), Unit.catalog_number)
            elif s.startswith('-'):
                stmt = stmt.order_by(desc(s[1:]))
            else:
                stmt = stmt.order_by(s)
    else:
        stmt = stmt.order_by(desc(Unit.id))

    # range / limit
    start, end = int(rng[0]), int(rng[1])
    if not (start == 0 and end == -1):
        limit = min((end - start), 2000)
        stmt = stmt.limit(limit)
        if start > 0:
            stmt = stmt.offset(start)

    begin_time = time.time()
    rows = session.execute(stmt).all()
    elapsed = time.time() - begin_time

    if total is None:
        subquery = base_stmt.subquery()
        total = session.execute(select(func.count()).select_from(subquery)).scalar()

    data = []
    for r in rows:
        if d := serialize_specimen_row(r, custom_area_class_ids):
            data.append(d)

    return jsonify({
        'data': data,
        'total': total,
        'elapsed': elapsed,
    })
