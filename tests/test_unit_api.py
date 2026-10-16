"""/api/v1/units: the generic, collection-agnostic unit API for admin clients.

Runs against the dev DB: builds two throwaway collections (one in site 1, one
in site 2), taxa, a person, records, units and a unit annotation type, and
removes them afterwards. Authenticates as an existing site-1 user (read only).
"""
import csv
import io
import json

import pytest
from flask_jwt_extended import create_access_token

from app.database import session
from app.models.collection import (
    AnnotationType,
    Collection,
    Person,
    Record,
    Unit,
    UnitAnnotation,
)
from app.models.site import User
from app.models.taxon import Taxon, TaxonRelation

DEAD = 'Dead (Disposed of; not retained.)'


@pytest.fixture()
def data(app):
    with app.app_context():
        user = User.query.filter(User.site_id == 1).order_by(User.id).first()
        assert user, 'dev DB needs a site-1 user'

        mine = Collection(name='pytest-unit-api', label='pytest A', site_id=1)
        other = Collection(name='pytest-unit-api-other', label='pytest B', site_id=2)
        person = Person(full_name='Pytest Collector')
        session.add_all([mine, other, person])

        taxa = {}
        for rank, name in [('genus', 'Pytestia'), ('section', 'Pytestia sect. Alpha'),
                           ('species', 'Pytestia beta'), ('species', 'Pytestia gamma')]:
            taxa[name] = Taxon(rank=rank, full_scientific_name=name)
            session.add(taxa[name])
        session.commit()
        gen, sec = taxa['Pytestia'], taxa['Pytestia sect. Alpha']
        gen.make_relations({})
        sec.make_relations({'genus': gen.id})
        taxa['Pytestia beta'].make_relations({'genus': gen.id, 'section': sec.id})
        taxa['Pytestia gamma'].make_relations({'genus': gen.id})

        room = AnnotationType(name='room', label='房間', target='unit', input_type='select',
                              collection_id=mine.id, data={'options': [['307', '307'], ['323', '323']]})
        session.add(room)

        def record(field_number, taxon):
            r = Record(collection_id=1, collector_id=person.id, field_number=str(field_number),
                       field_number_int=field_number, proxy_taxon_id=taxon.id if taxon else None,
                       proxy_taxon_scientific_name=taxon.full_scientific_name if taxon else None)
            session.add(r)
            return r

        r1 = record(90001, taxa['Pytestia beta'])
        r2 = record(90002, taxa['Pytestia gamma'])
        r3 = record(90050, None)
        session.commit()

        units = {
            'beta': Unit(record_id=r1.id, collection_id=mine.id, catalog_number='9', disposition='in collection', notes='pytest-note'),
            'gamma': Unit(record_id=r2.id, collection_id=mine.id, catalog_number='10', disposition=DEAD),
            'notaxon': Unit(record_id=r3.id, collection_id=mine.id, catalog_number='11', disposition='in collection'),
            'other': Unit(record_id=r1.id, collection_id=other.id, catalog_number='9'),
        }
        session.add_all(units.values())
        session.commit()
        session.add_all([
            UnitAnnotation(unit_id=units['beta'].id, annotation_type_id=room.id, value='323'),
            UnitAnnotation(unit_id=units['gamma'].id, annotation_type_id=room.id, value='307'),
        ])
        session.commit()

        token = create_access_token(identity=str(user.id))
        yield {
            'token': token,
            'mine': mine.id,
            'other': other.id,
            'room': room.id,
            'taxa': {k: v.id for k, v in taxa.items()},
            'units': {k: v.id for k, v in units.items()},
            'person': person.id,
        }

        session.rollback()
        unit_ids = [v.id for v in units.values()]
        taxon_ids = [v.id for v in taxa.values()]
        UnitAnnotation.query.filter(UnitAnnotation.unit_id.in_(unit_ids)).delete(synchronize_session=False)
        Unit.query.filter(Unit.id.in_(unit_ids)).delete(synchronize_session=False)
        Record.query.filter(Record.id.in_([r1.id, r2.id, r3.id])).delete(synchronize_session=False)
        AnnotationType.query.filter(AnnotationType.id == room.id).delete(synchronize_session=False)
        Collection.query.filter(Collection.id.in_([mine.id, other.id])).delete(synchronize_session=False)
        TaxonRelation.query.filter(TaxonRelation.child_id.in_(taxon_ids)).delete(synchronize_session=False)
        Taxon.query.filter(Taxon.id.in_(taxon_ids)).delete(synchronize_session=False)
        Person.query.filter(Person.id == person.id).delete(synchronize_session=False)
        session.commit()


@pytest.fixture()
def api(client, data):
    client.set_cookie('access_token_cookie', data['token'])

    def get(path, filtr=None, **params):
        if filtr is not None:
            params['filter'] = json.dumps(filtr)
        return client.get(path, query_string=params)
    return get


def _catalog_numbers(resp):
    assert resp.status_code == 200, resp.get_json()
    return [x['catalog_number'] for x in resp.get_json()['data']]


# --- auth & scope -----------------------------------------------------------

def test_requires_jwt(client, data):
    assert client.get('/api/v1/units').status_code == 401


def test_collection_outside_site_is_forbidden(api, data):
    assert api('/api/v1/units', {'collection_id': data['other']}).status_code == 403
    assert api(f'/api/v1/collections/{data["other"]}/annotation-types').status_code == 403


def test_me_lists_site_collections(api, data):
    names = [c['name'] for c in api('/api/v1/me').get_json()['collections']]
    assert 'pytest-unit-api' in names
    assert 'pytest-unit-api-other' not in names


# --- list & filters ---------------------------------------------------------

def test_scopes_by_unit_collection_not_record_collection(api, data):
    # the records sit in collection 1; the units must still be found by their own collection
    resp = api('/api/v1/units', {'collection_id': data['mine']})
    assert _catalog_numbers(resp) == ['9', '10', '11']  # natural order, not '10' < '9'
    assert resp.get_json()['total'] == 3


def test_row_shape(api, data):
    row = api('/api/v1/units', {'collection_id': data['mine'], 'catalog_number': '9'}).get_json()['data'][0]
    assert row['entity_key'] == f'u{data["units"]["beta"]}'
    assert row['collector']['full_name'] == 'Pytest Collector'
    assert row['taxon']['scientific_name'] == 'Pytestia beta'
    assert row['annotations'] == {'room': '323'}


@pytest.mark.parametrize('filtr, expected', [
    ({'q': 'pytest-note'}, ['9']),
    ({'q': '90002'}, ['10']),
    ({'q': 'Pytestia gam'}, ['10']),
    ({'field_number': '90001--90002'}, ['9', '10']),
    ({'disposition': DEAD}, ['10']),
    ({'disposition': {'not': [DEAD]}}, ['9', '11']),
    ({'catalog_number': ['9', '11']}, ['9', '11']),
])
def test_filters(api, data, filtr, expected):
    assert _catalog_numbers(api('/api/v1/units', {'collection_id': data['mine'], **filtr})) == expected


def test_collector_filter(api, data):
    resp = api('/api/v1/units', {'collection_id': data['mine'], 'collector_id': [data['person']]})
    assert _catalog_numbers(resp) == ['9', '10', '11']


def test_taxon_filter_includes_descendants(api, data):
    mine = data['mine']
    assert _catalog_numbers(api('/api/v1/units', {'collection_id': mine, 'taxon_id': [data['taxa']['Pytestia']]})) == ['9', '10']
    # the section holds beta only
    assert _catalog_numbers(api('/api/v1/units', {'collection_id': mine, 'taxon_id': [data['taxa']['Pytestia sect. Alpha']]})) == ['9']


def test_annotation_filter(api, data):
    room = str(data['room'])
    mine = data['mine']
    assert _catalog_numbers(api('/api/v1/units', {'collection_id': mine, 'annotations': {room: ['323']}})) == ['9']
    # units without a room are "not 323" too
    assert _catalog_numbers(api('/api/v1/units', {'collection_id': mine, 'annotations': {room: {'not': ['323']}}})) == ['10', '11']


def test_range_and_sort(api, data):
    resp = api('/api/v1/units', {'collection_id': data['mine']}, range='[1,2]', sort='-catalog_number')
    assert _catalog_numbers(resp) == ['10']
    assert resp.get_json()['total'] == 3


@pytest.mark.parametrize('params', [
    {'filter': '{not json'},
    {'filter': '{"field_number": "a--b"}'},
    {'sort': 'nope'},
    {'range': '[5,1]'},
])
def test_bad_input_is_400(client, data, params):
    client.set_cookie('access_token_cookie', data['token'])
    assert client.get('/api/v1/units', query_string=params).status_code == 400


# --- facets -----------------------------------------------------------------

def test_facets(api, data):
    resp = api('/api/v1/units/facets', {'collection_id': data['mine']},
               fields=f'disposition,annotation:{data["room"]},taxon')
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert {x['value']: x['count'] for x in body['facets']['disposition']} == {'in collection': 2, DEAD: 1}
    assert {x['value']: x['count'] for x in body['facets'][f'annotation:{data["room"]}']} == {'323': 1, '307': 1, None: 1}
    assert {x['label'] for x in body['facets']['taxon'] if x['value']} == {'Pytestia beta', 'Pytestia gamma'}
    assert body['summary'] == {'units': 3, 'taxa': 2, 'units_without_taxon': 1}


def test_unknown_facet_is_400(api, data):
    assert api('/api/v1/units/facets', {'collection_id': data['mine']}, fields='nope').status_code == 400


# --- export & annotation types ----------------------------------------------

def test_export_csv(api, data):
    resp = api('/api/v1/units/export', {'collection_id': data['mine']}, format='csv')
    assert resp.status_code == 200
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True).lstrip('﻿'))))
    header = rows[0]
    assert header[:3] == ['unit_id', 'catalog_number', 'field_number']
    assert header[-1] == 'room'
    assert [r[1] for r in rows[1:]] == ['9', '10', '11']
    assert rows[1][-1] == '323'


def test_export_xlsx(api, data):
    resp = api('/api/v1/units/export', {'collection_id': data['mine']}, format='xlsx')
    assert resp.status_code == 200
    assert resp.get_data()[:2] == b'PK'  # zip container


def test_annotation_types(api, data):
    types = api(f'/api/v1/collections/{data["mine"]}/annotation-types').get_json()
    assert [(t['name'], t['input_type']) for t in types] == [('room', 'select')]
    assert types[0]['options'][0] == ['307', '307']


# --- CORS & login redirect --------------------------------------------------

def test_cors_echoes_only_allowed_origin(app, client, data):
    app.config['CORS_ORIGINS'] = ['https://client.example.org']
    client.set_cookie('access_token_cookie', data['token'])
    allowed = client.get('/api/v1/me', headers={'Origin': 'https://client.example.org'})
    assert allowed.headers['Access-Control-Allow-Origin'] == 'https://client.example.org'
    assert allowed.headers['Access-Control-Allow-Credentials'] == 'true'
    denied = client.get('/api/v1/me', headers={'Origin': 'https://evil.example.org'})
    assert 'Access-Control-Allow-Origin' not in denied.headers


@pytest.mark.parametrize('next_url, expected', [
    (None, '/admin'),
    ('/admin/records/', '/admin/records/'),
    ('//evil.example.org/x', '/admin'),
    ('/\\evil.example.org', '/admin'),
    ('https://evil.example.org/', '/admin'),
    ('javascript:alert(1)', '/admin'),
    ('https://client.example.org/#/tag/1', 'https://client.example.org/#/tag/1'),
])
def test_safe_next_url(app, next_url, expected):
    from app.blueprints.admin import safe_next_url
    app.config['CORS_ORIGINS'] = ['https://client.example.org']
    with app.app_context():
        assert safe_next_url(next_url) == expected
