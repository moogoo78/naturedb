"""annotation_type.is_public: only opted-in unit annotation types reach the
public specimen page (Unit.get_data); the rest are internal.

Runs against the dev DB: builds a throwaway collection, record, unit and
annotation types, and removes them afterwards.
"""
import pytest

from app.database import session
from app.models.collection import AnnotationType, Collection, Record, Unit, UnitAnnotation


@pytest.fixture()
def data(app):
    with app.app_context():
        coll = Collection(name='pytest-anno-public', label='pytest anno', site_id=1, organization_id=1)
        session.add(coll)
        session.commit()
        record = Record(collection_id=coll.id, field_number='pytest-anno-1')
        session.add(record)
        session.commit()
        unit = Unit(record_id=record.id, collection_id=coll.id, catalog_number='pytest-anno')
        public = AnnotationType(name='pytest_public', label='Public note', target='unit', input_type='input', sort=1, collection_id=coll.id, is_public=True)
        hidden = AnnotationType(name='pytest_hidden', label='Hidden flag', target='unit', input_type='input', sort=2, collection_id=coll.id)
        check = AnnotationType(name='pytest_check', label='Cultivated', target='unit', input_type='checkbox', sort=3, collection_id=coll.id, is_public=True)
        session.add_all([unit, public, hidden, check])
        session.commit()
        types = [public, hidden, check]
        session.add_all([
            UnitAnnotation(unit_id=unit.id, annotation_type_id=public.id, value='seen'),
            UnitAnnotation(unit_id=unit.id, annotation_type_id=hidden.id, value='date-error'),
            UnitAnnotation(unit_id=unit.id, annotation_type_id=check.id, value='on'),
        ])
        session.commit()

        yield {'unit': unit, 'types': types}

        session.rollback()
        UnitAnnotation.query.filter(UnitAnnotation.unit_id == unit.id).delete()
        AnnotationType.query.filter(AnnotationType.id.in_([t.id for t in types])).delete()
        Unit.query.filter(Unit.id == unit.id).delete()
        Record.query.filter(Record.id == record.id).delete()
        Collection.query.filter(Collection.id == coll.id).delete()
        session.commit()


def test_new_type_defaults_hidden(app, data):
    with app.app_context():
        assert data['types'][1].is_public is False


def test_get_data_only_public_types(app, data):
    with app.test_request_context():  # get_data builds URLs
        annotations = data['unit'].get_data()['annotations']
        labels = [a[0] for a in annotations]
        assert 'Hidden flag' not in labels
        assert ['Public note', 'seen'] in annotations


def test_checkbox_shows_check_mark(app, data):
    with app.test_request_context():
        assert ['Cultivated', '✓'] in data['unit'].get_data()['annotations']


def test_unit_template_renders_annotations(app, data):
    with app.test_request_context():
        from flask import render_template_string
        html = render_template_string(
            # info() lives in specimen-detail.html; a stub is enough here
            '{% macro info(f, v) %}{{ f }}: {{ v }}{% endmacro %}{% include "_inc_specimen_unit.html" %}',
            data={'specimen': data['unit'].get_data()},
        )
        assert 'Public note' in html
        assert 'seen' in html
        assert 'Hidden flag' not in html
        assert 'date-error' not in html
