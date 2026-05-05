"""Unit tests for app.services.ai — dispatcher, Anthropic backend, remote backend.

These tests mock external dependencies (Anthropic SDK, sockets, image fetch)
so they don't need ANTHROPIC_API_KEY, a running worker, or live S3 access.
"""
import base64
import json
import os
import socket
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai import (
    BackendError,
    BackendTimeout,
    BackendUnavailable,
    NoCoverImage,
    PROMPT_VERSION,
    extract_label,
)
from app.services.ai import anthropic_backend, extractor, remote_backend


# ---------- Dispatcher: backend selection -----------------------------------


def test_dispatcher_rejects_unknown_backend():
    """9.3: dispatcher raises ValueError on unsupported backend."""
    fake_unit = MagicMock()
    fake_unit.id = 1
    with pytest.raises(ValueError, match='unsupported backend'):
        extract_label(fake_unit, backend='openai')


def test_dispatcher_returns_cached_row_when_present(monkeypatch):
    """9.1: cache hit returns persisted text without calling backend."""
    fake_unit = MagicMock()
    fake_unit.id = 42

    cached = MagicMock()
    cached.id = 7
    cached.text = 'cached label text'
    cached.source_data = {
        'model': 'claude-test', 'backend': 'api',
        'ms': 999, 'image_size': '2048',
    }
    monkeypatch.setattr(extractor, '_latest_cached', lambda unit_id: cached)
    # If the dispatcher tried to fetch the image or call a backend, this fails:
    monkeypatch.setattr(extractor, '_fetch_cover_image_bytes', lambda *a, **k: pytest.fail('should not fetch image'))

    result = extract_label(fake_unit, backend='api', force=False)
    assert result.cached is True
    assert result.text == 'cached label text'
    assert result.model == 'claude-test'
    assert result.verbatim_id == 7


def test_dispatcher_force_appends_new_row(monkeypatch):
    """9.2 (revised): force=True bypasses cache and appends a new row.

    UnitVerbatim is append-only — every call inserts. Cache lookup returns the
    most-recent matching row but force always inserts.
    """
    fake_unit = MagicMock()
    fake_unit.id = 42

    # Pretend a cache row exists; with force=True it must be ignored.
    monkeypatch.setattr(extractor, '_latest_cached', lambda uid: MagicMock())
    monkeypatch.setattr(extractor, '_fetch_cover_image_bytes', lambda *a, **k: b'jpeg-bytes')

    fresh_result = extractor.ExtractionResult(
        text='fresh', model='claude-x', backend='api', ms=123,
    )
    fake_backend = MagicMock(return_value=fresh_result)
    persist_calls = []
    monkeypatch.setattr(extractor, '_persist', lambda uid, user, r: persist_calls.append((uid, user, r)) or 99)

    # Patch the dynamic import the dispatcher uses
    import app.services.ai.anthropic_backend as ab
    monkeypatch.setattr(ab, 'extract', fake_backend)

    result = extract_label(fake_unit, backend='api', force=True, user_id=5)

    assert result.cached is False
    assert result.text == 'fresh'
    assert result.verbatim_id == 99
    assert fake_backend.call_count == 1
    assert len(persist_calls) == 1
    assert persist_calls[0][0] == 42  # unit_id
    assert persist_calls[0][1] == 5   # user_id


# ---------- Anthropic backend payload shape ---------------------------------


def test_anthropic_backend_payload_has_cache_control(monkeypatch):
    """9.4: API backend marks both system prompt and image with cache_control."""
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')

    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            reply = MagicMock()
            block = MagicMock()
            block.type = 'text'
            block.text = 'fake transcription'
            reply.content = [block]
            return reply

    class FakeAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = FakeMessages()

    # Patch the SDK reference inside the backend module
    monkeypatch.setattr(
        'app.services.ai.anthropic_backend.Anthropic',
        FakeAnthropic,
        raising=False,
    )

    # Inject a stub Anthropic into the module namespace so `from anthropic import Anthropic` succeeds
    import sys
    fake_module = type(sys)('anthropic')
    fake_module.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, 'anthropic', fake_module)

    result = anthropic_backend.extract(b'fake-jpeg-bytes', prompt_version='label-v1')

    assert result.text == 'fake transcription'
    assert result.backend == 'api'
    assert result.model == anthropic_backend.DEFAULT_MODEL

    # System prompt block has cache_control
    sys_blocks = captured['system']
    assert isinstance(sys_blocks, list) and sys_blocks
    assert sys_blocks[0]['cache_control']['type'] == 'ephemeral'

    # Image content block has cache_control
    user_msg = captured['messages'][0]
    image_block = next(b for b in user_msg['content'] if b['type'] == 'image')
    assert image_block['cache_control']['type'] == 'ephemeral'
    assert image_block['source']['type'] == 'base64'
    assert image_block['source']['media_type'] == 'image/jpeg'
    # Round-trip the base64 to confirm the right bytes were sent
    assert base64.b64decode(image_block['source']['data']) == b'fake-jpeg-bytes'


def test_anthropic_backend_missing_key_raises(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    with pytest.raises(BackendError, match='ANTHROPIC_API_KEY'):
        anthropic_backend.extract(b'jpg', prompt_version='label-v1')


# ---------- Remote backend socket handling ---------------------------------


def test_remote_backend_missing_socket_raises_unavailable(monkeypatch):
    """9.5: socket file missing → BackendUnavailable."""
    monkeypatch.setenv('AI_LABEL_REMOTE_SOCKET', '/tmp/definitely-does-not-exist-' + os.urandom(4).hex() + '.sock')
    with pytest.raises(BackendUnavailable, match='not found'):
        remote_backend.extract(b'jpg', prompt_version='label-v1')


def test_remote_backend_round_trip_via_real_socket(tmp_path, monkeypatch):
    """End-to-end: real Unix socket, fake worker thread, parses the reply."""
    import threading

    sock_path = str(tmp_path / 'test-worker.sock')
    monkeypatch.setenv('AI_LABEL_REMOTE_SOCKET', sock_path)
    monkeypatch.setenv('AI_LABEL_REMOTE_TIMEOUT', '5')

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    received = {}

    def fake_worker():
        conn, _ = server.accept()
        with conn:
            buf = b''
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if b'\n' in buf:
                    break
            received['raw'] = buf
            conn.sendall((json.dumps({
                'text': 'fake-worker reply',
                'model': 'remote-fake',
            }) + '\n').encode())

    t = threading.Thread(target=fake_worker, daemon=True)
    t.start()

    try:
        result = remote_backend.extract(b'jpeg-bytes', prompt_version='label-v1', model='claude-test')
    finally:
        server.close()
        t.join(timeout=2)

    assert result.text == 'fake-worker reply'
    assert result.backend == 'remote'
    assert result.model == 'remote-fake'
    # Verify worker received correct payload shape
    req = json.loads(received['raw'].split(b'\n', 1)[0].decode())
    assert base64.b64decode(req['image_b64']) == b'jpeg-bytes'
    assert req['prompt_version'] == 'label-v1'
    assert req['model'] == 'claude-test'


def test_fetch_ai_extractions_shape(monkeypatch):
    """9.8: fetch_ai_extractions returns the expected dict shape per unit."""
    from datetime import datetime
    from app.exporters import scribe

    fake_now = datetime(2026, 5, 4, 12, 0, 0)
    fake_rows = [
        # (id, unit_id, text, created, source_data)
        (1, 100, 'unit-100 text', fake_now, {
            'backend': 'api', 'model': 'claude-x',
            'prompt_version': 'label-v1', 'image_size': '2048', 'ms': 1500,
        }),
        (2, 200, 'unit-200 text', fake_now, {
            'backend': 'remote', 'model': 'remote-stub',
            'prompt_version': 'label-v1', 'image_size': '2048', 'ms': 800,
        }),
    ]

    class FakeResult:
        def all(self):
            return fake_rows

    monkeypatch.setattr(scribe.session, 'execute', lambda stmt: FakeResult())

    out = scribe.fetch_ai_extractions({100, 200, 300})

    assert set(out.keys()) == {100, 200}
    assert out[100]['text'] == 'unit-100 text'
    assert out[100]['model'] == 'claude-x'
    assert out[100]['backend'] == 'api'
    assert out[100]['ms'] == 1500
    assert out[100]['created_at'] == '2026-05-04T12:00:00'
    assert out[200]['backend'] == 'remote'
    # 300 had no rows → not present (the per-item dict gets None via .get())
    assert 300 not in out


def test_fetch_ai_extractions_empty_input():
    """No unit_ids → empty dict, no query."""
    from app.exporters import scribe
    assert scribe.fetch_ai_extractions(set()) == {}
    assert scribe.fetch_ai_extractions([]) == {}


def test_remote_backend_worker_returns_error(tmp_path, monkeypatch):
    import threading

    sock_path = str(tmp_path / 'test-worker.sock')
    monkeypatch.setenv('AI_LABEL_REMOTE_SOCKET', sock_path)
    monkeypatch.setenv('AI_LABEL_REMOTE_TIMEOUT', '5')

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    def fake_worker():
        conn, _ = server.accept()
        with conn:
            conn.recv(65536)
            conn.sendall((json.dumps({'error': 'bridge crashed'}) + '\n').encode())

    t = threading.Thread(target=fake_worker, daemon=True)
    t.start()

    try:
        with pytest.raises(BackendError, match='bridge crashed'):
            remote_backend.extract(b'x', prompt_version='label-v1')
    finally:
        server.close()
        t.join(timeout=2)
