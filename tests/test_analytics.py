"""Tests for the GA4 dashboard summary helper (app/helpers_analytics.py).

The GA4 Data API is an external dependency, so these tests never hit the
network: they mock the token minting and report calls. The contract under
test is that the helper degrades gracefully (returns None, never raises) and
parses report payloads into the shape the dashboard template expects.
"""
from unittest.mock import patch

import pytest

import app.helpers_analytics as ga
from app.utils import delete_cache


@pytest.fixture(autouse=True)
def _clear_cache(app):
    with app.app_context():
        delete_cache(ga.CACHE_KEY)
    yield
    with app.app_context():
        delete_cache(ga.CACHE_KEY)


def test_returns_none_when_feature_disabled(app):
    app.config['FEATURE_GA_DASHBOARD'] = False
    with app.app_context():
        assert ga.get_ga_stats() is None


def test_returns_none_when_property_id_missing(app):
    app.config['FEATURE_GA_DASHBOARD'] = True
    app.config['GA4_PROPERTY_ID'] = None
    with app.app_context():
        assert ga.get_ga_stats() is None


def test_api_failure_is_swallowed(app):
    app.config['FEATURE_GA_DASHBOARD'] = True
    app.config['GA4_PROPERTY_ID'] = '123456789'
    with app.app_context():
        with patch.object(ga, '_get_access_token', side_effect=Exception('boom')):
            assert ga.get_ga_stats() is None


def test_happy_path_parsing(app):
    app.config['FEATURE_GA_DASHBOARD'] = True
    app.config['GA4_PROPERTY_ID'] = '123456789'

    reports = iter([
        {'rows': [{'metricValues': [
            {'value': '1500'}, {'value': '2000'}, {'value': '8000'}]}]},
        {'rows': [
            {'dimensionValues': [{'value': '/'}], 'metricValues': [{'value': '5000'}]},
            {'dimensionValues': [{'value': '/search'}], 'metricValues': [{'value': '3000'}]},
        ]},
        {'rows': [
            {'dimensionValues': [{'value': '20260701'}], 'metricValues': [{'value': '40'}]},
            {'dimensionValues': [{'value': '20260702'}], 'metricValues': [{'value': '55'}]},
        ]},
    ])

    with app.app_context():
        with patch.object(ga, '_get_access_token', return_value='tok'), \
             patch.object(ga, '_run_report', side_effect=lambda *a, **k: next(reports)):
            result = ga.get_ga_stats()

    assert result == {
        'active_users': 1500,
        'sessions': 2000,
        'page_views': 8000,
        'top_pages': [
            {'path': '/', 'views': 5000},
            {'path': '/search', 'views': 3000},
        ],
        'trend': {
            'labels': ['2026-07-01', '2026-07-02'],
            'data': [40, 55],
        },
    }


def test_empty_reports_yield_zeros(app):
    app.config['FEATURE_GA_DASHBOARD'] = True
    app.config['GA4_PROPERTY_ID'] = '123456789'

    with app.app_context():
        with patch.object(ga, '_get_access_token', return_value='tok'), \
             patch.object(ga, '_run_report', return_value={'rows': []}):
            result = ga.get_ga_stats()

    assert result['active_users'] == 0
    assert result['sessions'] == 0
    assert result['page_views'] == 0
    assert result['top_pages'] == []
    assert result['trend'] == {'labels': [], 'data': []}
