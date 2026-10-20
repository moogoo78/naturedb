"""A user assigned to some collections (user_collection) sees and edits only those.

Runs against the dev DB: builds two throwaway site-1 collections with one
record/unit each and a throwaway user limited to the first, and removes them
afterwards.
"""
import json

import pytest
from flask_jwt_extended import create_access_token, get_csrf_token

from app.database import session
from app.models.collection import Collection, Record, Unit
from app.models.site import User


@pytest.fixture()
def data(app):
    with app.app_context():
        mine = Collection(name='pytest-scope-mine', label='pytest mine', site_id=1, organization_id=1)
        other = Collection(name='pytest-scope-other', label='pytest other', site_id=1, organization_id=1)
        session.add_all([mine, other])
        session.commit()

        r_mine = Record(collection_id=mine.id, field_number='scope-1')
        r_other = Record(collection_id=other.id, field_number='scope-2')
        session.add_all([r_mine, r_other])
        session.commit()
        u_mine = Unit(record_id=r_mine.id, collection_id=mine.id, catalog_number='SCOPE1')
        u_other = Unit(record_id=r_other.id, collection_id=other.id, catalog_number='SCOPE2')
        limited = User(username='pytest-scope-user', site_id=1, role=User.ROLE_CATALOGER)
        limited.collections.append(mine)
        whole = User(username='pytest-scope-whole', site_id=1, role=User.ROLE_CATALOGER)
        session.add_all([u_mine, u_other, limited, whole])
        session.commit()

        yield {
            'mine': mine.id,
            'other': other.id,
            'records': {'mine': r_mine.id, 'other': r_other.id},
            'units': {'mine': u_mine.id, 'other': u_other.id},
            'limited': limited.id,
            'whole': whole.id,
        }

        session.rollback()
        User.query.filter(User.id.in_([limited.id, whole.id])).delete(synchronize_session=False)
        Unit.query.filter(Unit.id.in_([u_mine.id, u_other.id])).delete(synchronize_session=False)
        Record.query.filter(Record.id.in_([r_mine.id, r_other.id])).delete(synchronize_session=False)
        Collection.query.filter(Collection.id.in_([mine.id, other.id])).delete(synchronize_session=False)
        session.commit()


def _login(app, client, user_id):
    """flask-login session (admin pages) + JWT cookie (admin/unit APIs)"""
    with app.app_context():
        token = create_access_token(identity=str(user_id))
        csrf = get_csrf_token(token)
    client.set_cookie('access_token_cookie', token)
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
    return {'X-CSRF-TOKEN': csrf}


@pytest.fixture()
def limited(app, client, data):
    return _login(app, client, data['limited'])


def _units(client, filtr=None):
    params = {'filter': json.dumps(filtr)} if filtr is not None else {}
    return client.get('/api/v1/units', query_string=params)


def test_collection_ids_falls_back_to_site(app, data):
    with app.app_context():
        assert session.get(User, data['limited']).collection_ids == [data['mine']]
        whole = session.get(User, data['whole'])
        assert data['mine'] in whole.collection_ids
        assert data['other'] in whole.collection_ids


def test_unit_api_lists_only_assigned_collections(client, data, limited):
    resp = _units(client)
    assert resp.status_code == 200, resp.get_json()
    catalog_numbers = [x['catalog_number'] for x in resp.get_json()['data']]
    assert 'SCOPE1' in catalog_numbers
    assert 'SCOPE2' not in catalog_numbers
    assert _units(client, {'collection_id': data['other']}).status_code == 403
    assert client.get(f'/api/v1/collections/{data["other"]}/annotation-types').status_code == 403


def test_me_lists_only_assigned_collections(client, data, limited):
    ids = [c['id'] for c in client.get('/api/v1/me').get_json()['collections']]
    assert ids == [data['mine']]


def test_record_form_outside_scope_is_404(client, data, limited):
    assert client.get(f'/admin/records/r{data["records"]["mine"]}').status_code == 200
    assert client.get(f'/admin/records/r{data["records"]["other"]}').status_code == 404
    assert client.get(f'/admin/records/create?collection_id={data["other"]}').status_code == 403


def test_record_item_api_outside_scope_is_403(app, client, data, limited):
    other_id = data['records']['other']
    assert client.get(f'/admin/api/records/{data["records"]["mine"]}').status_code == 200
    assert client.get(f'/admin/api/records/{other_id}').status_code == 403
    assert client.patch(f'/admin/api/records/{other_id}', json={}, headers=limited).status_code == 403
    assert client.delete(f'/admin/api/records/{other_id}', headers=limited).status_code == 403
    assert client.post('/admin/api/records/', json={'collection_id': data['other']}, headers=limited).status_code == 403
    with app.app_context():
        assert session.get(Record, other_id) is not None


def test_unit_endpoints_outside_scope_are_403(app, client, data, limited):
    other_id = data['units']['other']
    assert client.post(f'/admin/api/units/{other_id}/simple-edit', data={}, headers=limited).status_code == 403
    assert client.post(f'/admin/api/units/{other_id}/media', headers=limited).status_code == 403
    assert client.get(f'/admin/units/{other_id}/simple-entry').status_code == 404

    resp = client.post('/admin/api/quick-edit', json={'item_key': f'u{other_id}', 'field_number': 'hacked'})
    assert resp.get_json()['message'] == 'error'
    with app.app_context():
        assert session.get(Record, data['records']['other']).field_number == 'scope-2'


def test_anonymous_unit_media_is_403(client, data):
    assert client.post(f'/admin/api/units/{data["units"]["mine"]}/media').status_code == 403


def test_collection_options_outside_scope_is_403(client, data, limited):
    assert client.get(f'/admin/api/collections/{data["other"]}/options').status_code == 403
