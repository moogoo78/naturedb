"""A user assigned to some collections (user_collection) sees and edits only those.

Runs against the dev DB: builds two throwaway site-1 collections with one
record/unit each and a throwaway user limited to the first, and removes them
afterwards.

Like prod's greenhouse, a unit's record may sit in another collection (`hosted`:
a mine-unit on an other-record) or be shared with units of other collections
(`shared`): access follows the record's units, and a shared record is read-only.
`viewer` is prod's greenhouse editor: edits `mine`, only views `other`.
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
        r_hosted = Record(collection_id=other.id, field_number='scope-3')
        r_shared = Record(collection_id=other.id, field_number='scope-4')
        session.add_all([r_mine, r_other, r_hosted, r_shared])
        session.commit()
        u_mine = Unit(record_id=r_mine.id, collection_id=mine.id, catalog_number='SCOPE1')
        u_other = Unit(record_id=r_other.id, collection_id=other.id, catalog_number='SCOPE2')
        u_hosted = Unit(record_id=r_hosted.id, collection_id=mine.id, catalog_number='SCOPE3')
        u_shared_mine = Unit(record_id=r_shared.id, collection_id=mine.id, catalog_number='SCOPE4')
        u_shared_other = Unit(record_id=r_shared.id, collection_id=other.id, catalog_number='SCOPE5')
        units = [u_mine, u_other, u_hosted, u_shared_mine, u_shared_other]
        records = [r_mine, r_other, r_hosted, r_shared]
        limited = User(username='pytest-scope-user', site_id=1, role=User.ROLE_CATALOGER)
        limited.set_collection_scope(mine)
        whole = User(username='pytest-scope-whole', site_id=1, role=User.ROLE_CATALOGER)
        viewer = User(username='pytest-scope-viewer', site_id=1, role=User.ROLE_CATALOGER)
        viewer.set_collection_scope(mine)
        viewer.set_collection_scope(other, can_edit=False)
        session.add_all(units + [limited, whole, viewer])
        session.commit()

        yield {
            'mine': mine.id,
            'other': other.id,
            'records': {'mine': r_mine.id, 'other': r_other.id, 'hosted': r_hosted.id, 'shared': r_shared.id},
            'units': {'mine': u_mine.id, 'other': u_other.id, 'hosted': u_hosted.id, 'shared': u_shared_mine.id},
            'limited': limited.id,
            'whole': whole.id,
            'viewer': viewer.id,
        }

        session.rollback()
        User.query.filter(User.id.in_([limited.id, whole.id, viewer.id])).delete(synchronize_session=False)
        Unit.query.filter(Unit.id.in_([x.id for x in units])).delete(synchronize_session=False)
        Record.query.filter(Record.id.in_([x.id for x in records])).delete(synchronize_session=False)
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


@pytest.fixture()
def viewer(app, client, data):
    return _login(app, client, data['viewer'])


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


def test_record_in_another_collection_follows_its_units(client, data, limited, monkeypatch):
    """prod greenhouse: collection-9 units on collection-1 records"""
    monkeypatch.setattr('app.blueprints.admin.put_entity', lambda *a, **kw: {'ok': True})
    hosted = data['records']['hosted']
    page = client.get(f'/admin/records/u{data["units"]["hosted"]}')
    assert page.status_code == 200
    assert 'id="unlock-button"' in page.get_data(as_text=True)
    assert client.get(f'/admin/api/records/{hosted}').status_code == 200
    assert client.patch(f'/admin/api/records/{hosted}', json={}, headers=limited).status_code == 200


def test_shared_record_is_read_only(app, client, data, limited):
    shared = data['records']['shared']
    page = client.get(f'/admin/records/r{shared}')
    assert page.status_code == 200
    assert 'id="unlock-button"' not in page.get_data(as_text=True)
    assert client.get(f'/admin/api/records/{shared}').status_code == 200
    assert client.patch(f'/admin/api/records/{shared}', json={}, headers=limited).status_code == 403
    assert client.delete(f'/admin/api/records/{shared}', headers=limited).status_code == 403
    unit_id = data['units']['shared']
    assert client.post(f'/admin/api/units/{unit_id}/simple-edit', json={}, headers=limited).status_code == 403
    resp = client.post('/admin/api/quick-edit', json={'item_key': f'u{unit_id}', 'field_number': 'hacked'})
    assert resp.get_json()['message'] == 'error'
    with app.app_context():
        assert session.get(Record, shared).field_number == 'scope-4'


def test_shared_record_is_editable_for_whole_site_user(app, client, data):
    _login(app, client, data['whole'])
    page = client.get(f'/admin/records/r{data["records"]["shared"]}')
    assert page.status_code == 200
    assert 'id="unlock-button"' in page.get_data(as_text=True)


# --- view-only collections (user_collection.can_edit = false) ---------------

def test_view_and_edit_ids(app, data):
    with app.app_context():
        user = session.get(User, data['viewer'])
        assert sorted(user.collection_ids) == sorted([data['mine'], data['other']])
        assert user.editable_collection_ids == [data['mine']]
        whole = session.get(User, data['whole'])
        assert whole.editable_collection_ids == whole.collection_ids


def test_view_only_collection_is_listed_and_searchable(app, client, data, viewer, monkeypatch):
    collections = {c['id']: c['can_edit'] for c in client.get('/api/v1/me').get_json()['collections']}
    assert collections == {data['mine']: True, data['other']: False}
    resp = _units(client, {'collection_id': data['other']})
    assert resp.status_code == 200
    assert sorted(x['catalog_number'] for x in resp.get_json()['data']) == ['SCOPE2', 'SCOPE5']
    # the record form of a hosted record loads the record collection's options
    from app.models.site import Site
    monkeypatch.setattr('app.helpers.get_current_site', lambda request: session.get(Site, 1))
    resp = client.get(f'/admin/api/collections/{data["other"]}/options')
    assert resp.status_code == 200


def test_view_only_collection_is_not_editable(app, client, data, viewer):
    other_record = data['records']['other']
    page = client.get(f'/admin/records/r{other_record}')
    assert page.status_code == 200
    assert 'id="unlock-button"' not in page.get_data(as_text=True)
    assert client.patch(f'/admin/api/records/{other_record}', json={}, headers=viewer).status_code == 403
    assert client.post('/admin/api/records/', json={'collection_id': data['other']}, headers=viewer).status_code == 403
    assert client.get(f'/admin/records/create?collection_id={data["other"]}').status_code == 403
    other_unit = data['units']['other']
    assert client.post(f'/admin/api/units/{other_unit}/media', headers=viewer).status_code == 403
    assert client.post(f'/admin/api/units/{other_unit}/simple-edit', json={}, headers=viewer).status_code == 403
    # hosted record: every unit editable, so the record is too
    page = client.get(f'/admin/records/r{data["records"]["hosted"]}')
    assert 'id="unlock-button"' in page.get_data(as_text=True)


def _new_unit_collection_id(app, user_id, record_id):
    from flask_login import login_user
    from app.blueprints.admin import new_unit_collection_id
    with app.test_request_context():
        login_user(session.get(User, user_id))
        return new_unit_collection_id(session.get(Record, record_id))


def test_new_unit_goes_to_an_editable_collection(app, data):
    # hosted record sits in `other`, which the viewer cannot edit
    assert _new_unit_collection_id(app, data['viewer'], data['records']['hosted']) == data['mine']
    assert _new_unit_collection_id(app, data['limited'], data['records']['hosted']) == data['mine']
    # unrestricted users keep the record's collection
    assert _new_unit_collection_id(app, data['whole'], data['records']['hosted']) == data['other']
    assert _new_unit_collection_id(app, data['viewer'], data['records']['mine']) == data['mine']


def test_put_entity_files_new_unit_in_given_collection(app, data, monkeypatch):
    from app import helpers
    captured = {}

    def fake_create(d):
        captured.update(d)
        raise RuntimeError('stop')
    monkeypatch.setattr(helpers.Unit, 'create_from_dict', staticmethod(fake_create))
    with app.test_request_context():
        record = session.get(Record, data['records']['hosted'])
        payload = {'identifications': {}, 'named_areas': {}, 'assertions': {}, 'record_groups': [],
                   'units': {'0': {'assertions': {}, 'annotations': {}}}}
        try:
            helpers.put_entity(record, payload, record.collection, 1, unit_collection_id=data['mine'])
        except Exception as e:
            captured.setdefault('error', repr(e))
        session.rollback()
    assert captured.get('collection_id') == data['mine'], captured


# --- logout -------------------------------------------------------------------

def test_logout_clears_the_jwt_cookie(app, client, data):
    _login(app, client, data['limited'])
    assert client.get('/api/v1/me').status_code == 200
    resp = client.get('/admin/logout?next=/admin/records/')
    assert resp.status_code == 302
    assert '/admin/login?next=/admin/records/' in resp.headers['Location']
    assert client.get('/api/v1/me').status_code == 401


def test_logout_drops_an_unsafe_next(client):
    resp = client.get('/admin/logout?next=//evil.example')
    assert 'evil.example' not in resp.headers['Location']
