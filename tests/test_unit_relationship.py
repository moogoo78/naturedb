"""unit_relationship: Darwin Core ResourceRelationship between units, which
replaced unit.parent_id and the propagation table.

Runs against the dev DB: builds throwaway collections (site 1 and site 2), a
record and units, and removes them afterwards.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app import helpers
from app.database import session
from app.models.collection import Collection, Record, Unit, UnitRelationship


@pytest.fixture()
def data(app):
    with app.app_context():
        mine = Collection(name='pytest-unit-rel', label='pytest A', site_id=1, organization_id=1)
        other = Collection(name='pytest-unit-rel-other', label='pytest B', site_id=2, organization_id=1)
        session.add_all([mine, other])
        session.commit()
        record = Record(collection_id=mine.id, field_number='pytest-rel-1')
        foreign_record = Record(collection_id=other.id, field_number='pytest-rel-2')
        session.add_all([record, foreign_record])
        session.commit()
        source = Unit(record_id=record.id, collection_id=mine.id, catalog_number='pytest-src')
        foreign = Unit(record_id=foreign_record.id, collection_id=other.id, catalog_number='pytest-foreign')
        session.add_all([source, foreign])
        session.commit()

        yield {'mine': mine, 'other': other, 'record': record, 'source': source, 'foreign': foreign}

        session.rollback()
        for r in (record, foreign_record):
            Unit.query.filter(Unit.record_id == r.id).delete()
        session.commit()
        Record.query.filter(Record.id.in_([record.id, foreign_record.id])).delete()
        Collection.query.filter(Collection.id.in_([mine.id, other.id])).delete()
        session.commit()


def _unit_payload(**kw):
    return {'assertions': {}, 'annotations': {}, **kw}


def _put_units(record, collection, units):
    payload = {'identifications': {}, 'named_areas': {}, 'assertions': {}, 'units': units}
    return helpers.put_entity(record, payload, collection, uid=None)


def test_relationship_to_dict(app, data):
    with app.test_request_context():  # to_dict builds URLs
        child = Unit(record_id=data['record'].id, collection_id=data['mine'].id, catalog_number='pytest-child')
        child.relationships.append(UnitRelationship(
            related_unit_id=data['source'].id, relationship_of_resource='derived from', remarks='half sheet'))
        session.add(child)
        session.commit()

        rels = child.to_dict()['relationships']
        assert len(rels) == 1
        assert rels[0]['related_unit_id'] == data['source'].id
        assert rels[0]['relationship_of_resource'] == 'derived from'
        assert rels[0]['remarks'] == 'half sheet'
        assert rels[0]['established_date'] == ''
        assert 'parent_id' not in child.to_dict()


def test_unit_without_related_unit(app, data):
    """an event on one unit (e.g. seeds harvested) needs no related unit"""
    with app.test_request_context():  # to_dict builds URLs
        data['source'].relationships.append(UnitRelationship(relationship_of_resource='propagation', remarks='greenhouse'))
        session.commit()
        assert data['source'].to_dict()['relationships'][0]['related_unit_id'] is None


def test_not_related_to_itself(app, data):
    with app.app_context():
        src = data['source']
        session.add(UnitRelationship(unit_id=src.id, related_unit_id=src.id, relationship_of_resource='derived from'))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_deleting_units(app, data):
    """the subject's rows go with it; a deleted related unit leaves the row"""
    with app.app_context():
        src = data['source']
        a = Unit(record_id=data['record'].id, collection_id=data['mine'].id, catalog_number='pytest-a')
        b = Unit(record_id=data['record'].id, collection_id=data['mine'].id, catalog_number='pytest-b')
        session.add_all([a, b])
        session.commit()
        a.relationships.append(UnitRelationship(related_unit_id=src.id, relationship_of_resource='derived from'))
        src.relationships.append(UnitRelationship(related_unit_id=b.id, relationship_of_resource='duplicate of'))
        session.commit()
        a_rel, src_rel = a.relationships[0].id, src.relationships[0].id

        session.delete(a)
        session.commit()
        assert session.get(UnitRelationship, a_rel) is None

        session.delete(b)
        session.commit()
        session.expire_all()
        kept = session.get(UnitRelationship, src_rel)
        assert kept is not None and kept.related_unit_id is None


def test_derived_from_unit(app, data):
    with app.app_context():
        mine = data['mine']
        assert helpers._derived_from_unit(str(data['source'].id), mine).id == data['source'].id
        assert helpers._derived_from_unit(data['foreign'].id, mine) is None  # other site
        assert helpers._derived_from_unit('', mine) is None
        assert helpers._derived_from_unit('x', mine) is None
        assert helpers._derived_from_unit(None, mine) is None
        assert helpers._derived_from_unit(2**31 - 1, mine) is None


def test_put_entity_branch_creates_derived_from(app, data, monkeypatch):
    """the record form's branch button sends a new unit with derived_from"""
    monkeypatch.setattr(helpers, 'mint_ark_id', lambda site, unit: None)
    with app.app_context():
        record, mine, src = data['record'], data['mine'], data['source']
        _put_units(record, mine, {
            str(src.id): _unit_payload(id=str(src.id), catalog_number='pytest-src'),
            '': _unit_payload(id='', catalog_number='pytest-branch', derived_from=str(src.id)),
        })
        session.expire_all()
        branch = Unit.query.filter(Unit.record_id == record.id, Unit.catalog_number == 'pytest-branch').one()
        assert [(x.related_unit_id, x.relationship_of_resource) for x in branch.relationships] == [(src.id, 'derived from')]
        assert src.relationships == []


def test_put_entity_ignores_foreign_or_existing(app, data, monkeypatch):
    """derived_from from another site is dropped; on an existing unit it is read only"""
    monkeypatch.setattr(helpers, 'mint_ark_id', lambda site, unit: None)
    with app.app_context():
        record, mine, src = data['record'], data['mine'], data['source']
        _put_units(record, mine, {
            str(src.id): _unit_payload(id=str(src.id), catalog_number='pytest-src', derived_from=str(data['foreign'].id)),
            '': _unit_payload(id='', catalog_number='pytest-branch', derived_from=str(data['foreign'].id)),
        })
        session.expire_all()
        branch = Unit.query.filter(Unit.record_id == record.id, Unit.catalog_number == 'pytest-branch').one()
        assert branch.relationships == []
        assert session.get(Unit, src.id).relationships == []
