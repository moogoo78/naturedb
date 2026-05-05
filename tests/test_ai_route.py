"""Integration tests for POST /api/v1/scribe/units/<id>/ai/label.

Mocks `extract_label` so tests don't need a real Anthropic key, real worker,
or real cover image. Uses Flask-Login's LOGIN_DISABLED to bypass auth.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai import (
    BackendError,
    BackendTimeout,
    BackendUnavailable,
    NoCoverImage,
)
from app.services.ai.extractor import ExtractionResult


@pytest.fixture
def ai_app(app):
    """App with the AI feature enabled and login bypassed."""
    app.config.update({
        'FEATURE_AI_LABEL': True,
        'AI_LABEL_DEFAULT_BACKEND': 'api',
        'AI_LABEL_RATE_PER_HOUR': 3,
        'LOGIN_DISABLED': True,
    })
    # Reset the in-memory rate-limiter bucket between tests
    from app.blueprints import api as api_module
    api_module._AI_LABEL_BUCKETS.clear()
    yield app


@pytest.fixture
def fake_unit(monkeypatch):
    """Stub session.get(Unit, id) to return a fake unit instead of hitting DB."""
    unit = MagicMock()
    unit.id = 999
    unit.cover_image_id = 1
    from app.blueprints import api as api_module
    real_session = api_module.session

    def fake_get(model, oid):
        # Only intercept Unit lookups for our test id; pass through anything else
        if oid == 999 and getattr(model, '__name__', '') == 'Unit':
            return unit
        if oid == 9999 and getattr(model, '__name__', '') == 'Unit':
            return None
        return real_session.get(model, oid)

    monkeypatch.setattr(api_module.session, 'get', fake_get)
    # Avoid touching the DB on commit/rollback
    monkeypatch.setattr(api_module.session, 'commit', lambda: None)
    monkeypatch.setattr(api_module.session, 'rollback', lambda: None)
    return unit


# ---------- Feature flag --------------------------------------------------


def test_route_returns_404_when_feature_disabled(app, client):
    """9.6 prelude: route is hidden when FEATURE_AI_LABEL is false."""
    app.config['FEATURE_AI_LABEL'] = False
    app.config['LOGIN_DISABLED'] = True
    res = client.post('/api/v1/scribe/units/1/ai/label', json={'backend': 'api'})
    assert res.status_code == 404
    body = res.get_json()
    assert body['code'] == 'feature_off'


# ---------- Validation ----------------------------------------------------


def test_route_unknown_unit_returns_404(ai_app, client, fake_unit):
    res = client.post('/api/v1/scribe/units/9999/ai/label', json={'backend': 'api'})
    assert res.status_code == 404
    assert res.get_json()['code'] == 'not_found'


def test_route_bad_backend_returns_400(ai_app, client, fake_unit):
    res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'openai'})
    assert res.status_code == 400
    assert res.get_json()['code'] == 'bad_backend'


def test_route_bad_image_size_returns_400(ai_app, client, fake_unit):
    res = client.post('/api/v1/scribe/units/999/ai/label',
                      json={'backend': 'api', 'image_size': '8192'})
    assert res.status_code == 400
    assert res.get_json()['code'] == 'bad_size'


# ---------- Happy path + cache --------------------------------------------


def test_route_happy_path_returns_200_and_text(ai_app, client, fake_unit, monkeypatch):
    """9.6: happy path — mocked backend returns text, route returns 200."""
    fake_result = ExtractionResult(
        text='Quercus alba L.\nBerkshire Co., Mass.',
        model='claude-sonnet-4-6',
        backend='api',
        ms=1234,
        cached=False,
        verbatim_id=42,
    )
    monkeypatch.setattr(
        'app.blueprints.api.extract_label',
        lambda unit, **kw: fake_result,
    )

    res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'api'})
    assert res.status_code == 200
    body = res.get_json()
    assert body['text'].startswith('Quercus alba')
    assert body['model'] == 'claude-sonnet-4-6'
    assert body['backend'] == 'api'
    assert body['cached'] is False
    assert body['ms'] == 1234


def test_route_cached_result_does_not_consume_rate_limit(ai_app, client, fake_unit, monkeypatch):
    """Cached responses are free — bucket should not grow."""
    fake_result = ExtractionResult(
        text='cached text', model='m', backend='api', ms=0, cached=True,
    )
    monkeypatch.setattr(
        'app.blueprints.api.extract_label',
        lambda unit, **kw: fake_result,
    )

    from app.blueprints import api as api_module
    initial = sum(api_module._AI_LABEL_BUCKETS.values())

    for _ in range(5):
        res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'api'})
        assert res.status_code == 200
        assert res.get_json()['cached'] is True

    after = sum(api_module._AI_LABEL_BUCKETS.values())
    assert after == initial, 'cached responses should not count against rate limit'


# ---------- Backend exception mapping -------------------------------------


@pytest.mark.parametrize('exc, code, status', [
    (NoCoverImage('no img'), 'no_image', 422),
    (BackendUnavailable('worker down'), 'remote_down', 503),
    (BackendTimeout('60s'), 'remote_timeout', 504),
    (BackendError('rate limited'), 'backend_error', 502),
])
def test_route_maps_backend_exceptions(ai_app, client, fake_unit, monkeypatch, exc, code, status):
    """9.6 + spec: route translates each backend exception to the right HTTP code."""
    def boom(unit, **kw):
        raise exc
    monkeypatch.setattr('app.blueprints.api.extract_label', boom)

    res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'api'})
    assert res.status_code == status
    assert res.get_json()['code'] == code


# ---------- Rate limit ----------------------------------------------------


def test_route_returns_429_after_limit(ai_app, client, fake_unit, monkeypatch):
    """9.7: N+1 un-cached calls → 429 with rate_limit code and retry_after."""
    fake_result = ExtractionResult(
        text='t', model='m', backend='api', ms=10, cached=False,
    )
    monkeypatch.setattr(
        'app.blueprints.api.extract_label',
        lambda unit, **kw: fake_result,
    )

    # AI_LABEL_RATE_PER_HOUR=3 from the fixture; first 3 succeed, 4th hits the limit
    for _ in range(3):
        res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'api'})
        assert res.status_code == 200

    res = client.post('/api/v1/scribe/units/999/ai/label', json={'backend': 'api'})
    assert res.status_code == 429
    body = res.get_json()
    assert body['code'] == 'rate_limit'
    assert 'retry_after' in body and body['retry_after'] > 0


# ---------- Health check --------------------------------------------------


def test_health_returns_feature_off(app, client):
    app.config['FEATURE_AI_LABEL'] = False
    res = client.get('/api/v1/scribe/ai/health')
    assert res.status_code == 200
    body = res.get_json()
    assert body['feature'] is False
    assert body['remote_available'] is False


def test_health_reports_socket_state(ai_app, client, tmp_path, monkeypatch):
    """When socket file doesn't exist → remote_available=false."""
    nonexistent = tmp_path / 'no-such.sock'
    ai_app.config['AI_LABEL_REMOTE_SOCKET'] = str(nonexistent)
    res = client.get('/api/v1/scribe/ai/health')
    assert res.status_code == 200
    body = res.get_json()
    assert body['feature'] is True
    assert body['remote_available'] is False
    assert body['default_backend'] == 'api'
