'''Authenticated, collection-agnostic unit API for admin clients.

Clients (e.g. the greenhouse app, a separate repo) sit on their own subdomain
and call these with the JWT cookie set by /admin/login. Everything a client
needs to know about a collection's custom fields comes from
/collections/<id>/annotation-types, so nothing here is collection-specific.
See app/helpers_unit_query.py for the filter format.
'''
import csv
import io
import json
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    request,
)
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from app.database import session
from app.models.site import User
from app.blueprints.cors import allow_cors
from app.helpers_unit_query import (
    UnitQueryError,
    annotation_types,
    export_rows,
    facet_units,
    query_units,
    resolve_collection_ids,
)

unit_api = Blueprint('unit_api', __name__)
allow_cors(unit_api)


@unit_api.errorhandler(UnitQueryError)
def handle_query_error(e):
    return jsonify({'msg': str(e)}), 400


@unit_api.errorhandler(PermissionError)
def handle_permission_error(e):
    return jsonify({'msg': str(e)}), 403


def _user():
    return session.get(User, int(get_jwt_identity()))


def _site_collection_ids():
    user = _user()
    if not user or not user.site:
        raise PermissionError('user has no site')
    return user.site.collection_ids


def _json_arg(name, default):
    raw = request.args.get(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except ValueError:
        raise UnitQueryError(f'{name} is not valid JSON')


def _filter_and_collections():
    filtr = _json_arg('filter', {})
    if not isinstance(filtr, dict):
        raise UnitQueryError('filter must be a JSON object')
    return filtr, resolve_collection_ids(filtr, _site_collection_ids())


@unit_api.route('/me')
@jwt_required()
def get_me():
    user = _user()
    if not user:
        return jsonify({'msg': 'user not found'}), 401
    site = user.site
    collections = sorted(site.collections, key=lambda x: x.sort or 0) if site else []
    return jsonify({
        'id': user.id,
        'username': user.username,
        'site': {'id': site.id, 'name': site.name} if site else None,
        'collections': [{'id': c.id, 'name': c.name, 'label': c.label} for c in collections],
    })


@unit_api.route('/units')
@jwt_required()
def get_units():
    filtr, collection_ids = _filter_and_collections()
    start, end = _json_arg('range', [0, 50])
    return jsonify(query_units(filtr, collection_ids, request.args.get('sort'), start, end))


@unit_api.route('/units/facets')
@jwt_required()
def get_unit_facets():
    filtr, collection_ids = _filter_and_collections()
    fields = [x for x in request.args.get('fields', '').split(',') if x]
    limit = request.args.get('limit', 100, type=int)
    return jsonify(facet_units(filtr, collection_ids, fields, limit))


@unit_api.route('/units/export')
@jwt_required()
def export_units():
    filtr, collection_ids = _filter_and_collections()
    fmt = request.args.get('format', 'csv')
    if fmt not in ('csv', 'xlsx'):
        raise UnitQueryError('format must be csv or xlsx')

    header, rows = export_rows(filtr, collection_ids, request.args.get('sort'))
    filename = f'units-{datetime.now().strftime("%Y%m%d-%H%M%S")}.{fmt}'
    disposition = {'Content-Disposition': f'attachment; filename="{filename}"'}

    if fmt == 'csv':
        buf = io.StringIO()
        buf.write('﻿')  # BOM: Excel otherwise reads UTF-8 CSV as Big5/cp1252
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerows(rows)
        return Response(buf.getvalue(), mimetype='text/csv', headers=disposition)

    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        buf.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=disposition,
    )


@unit_api.route('/collections/<int:collection_id>/annotation-types')
@jwt_required()
def get_annotation_types(collection_id):
    if collection_id not in _site_collection_ids():
        raise PermissionError('collection not in this site')
    return jsonify(annotation_types([collection_id], request.args.get('target', 'unit')))
