"""Long-running worker that bridges the Flask remote_backend to a Claude session.

Run this as a separate process (NOT auto-started by Flask), using the SAME
Python environment as the Flask app (the `-m` runner imports `app.__init__`
which pulls in Flask, SQLAlchemy, etc.):

    # activate your venv first, then:
    python -m app.services.ai.remote_worker

The worker listens on a Unix-domain socket (AI_LABEL_REMOTE_SOCKET, default
/tmp/naturedb-ai-label.sock), accepts one connection at a time, reads a
single newline-terminated JSON request, calls _call_claude(), and writes a
newline-terminated JSON reply.

Protocol:
  request:  {"image_b64": "...", "prompt_version": "label-v1", "model": null}
  reply:    {"text": "...", "model": "claude-...", "ms": 1234}
        or  {"error": "<message>"}

The actual bridge to Claude (subprocess, MCP client, Agent SDK, etc.) is the
extension point _call_claude(image_bytes, prompt_version, model). The default
implementation returns a placeholder so the panel UI can be exercised end-to-
end without a real Claude session — replace it with your bridge of choice.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import signal
import socket
import sys
import time
from typing import Optional

logger = logging.getLogger(__name__)


SOCKET_PATH_DEFAULT = '/tmp/naturedb-ai-label.sock'
PLACEHOLDER_MODEL = 'remote-stub'


def _call_claude(image_bytes: bytes, prompt_version: str, model: Optional[str]) -> dict:
    """Bridge to a Claude session. **Replace this in your deployment.**

    Default implementation returns a placeholder so you can verify the
    JS panel + socket plumbing without wiring up a real Claude session yet.

    Suggested implementations:
      - subprocess: spawn `claude --print --output-format json` and pipe in
        an attachment + a label-extraction prompt. Parse stdout JSON.
      - Claude Agent SDK: use the Python SDK to drive a session with vision.
      - MCP client: connect to a Claude Code MCP endpoint and call a custom
        transcribe tool.

    The system prompt to use lives in app/services/ai/extractor.py
    (`LABEL_SYSTEM_PROMPT`); import it inside your bridge implementation
    rather than at module top so this file doesn't need DB connectivity
    for stub-mode runs.

    Returns: dict with at least 'text' and 'model'. May also include 'ms'.
    """
    logger.warning(
        'remote_worker._call_claude is a STUB returning placeholder text. '
        'See the docstring for how to wire in a real Claude bridge.'
    )
    return {
        'text': (
            '[remote-worker stub] No Claude bridge configured. '
            'See app/services/ai/remote_worker.py:_call_claude '
            f'(image: {len(image_bytes)} bytes, prompt_version: {prompt_version}, model: {model}).'
        ),
        'model': PLACEHOLDER_MODEL,
    }


def handle_request(raw: bytes) -> bytes:
    """Process one request line and produce one reply line."""
    started = time.monotonic()
    try:
        req = json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError as e:
        return _err(f'invalid JSON request: {e}')

    image_b64 = req.get('image_b64')
    if not image_b64:
        return _err('missing image_b64')

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return _err(f'invalid image_b64: {e}')

    prompt_version = req.get('prompt_version') or 'label-v1'
    model = req.get('model')

    try:
        result = _call_claude(image_bytes, prompt_version, model)
    except Exception as e:
        logger.exception('Claude bridge failed')
        return _err(f'claude bridge error: {e}')

    if 'ms' not in result:
        result['ms'] = int((time.monotonic() - started) * 1000)
    if 'text' not in result:
        return _err('bridge returned no text')

    return (json.dumps(result) + '\n').encode('utf-8')


def _err(msg: str) -> bytes:
    return (json.dumps({'error': msg}) + '\n').encode('utf-8')


def serve(socket_path: str) -> None:
    # Remove stale socket file if present
    try:
        os.unlink(socket_path)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning('could not remove stale socket %s: %s', socket_path, e)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)
    # Tighten permissions: only same user can connect.
    try:
        os.chmod(socket_path, 0o600)
    except OSError:
        pass
    sock.listen(8)
    logger.info('AI label remote-worker listening on %s', socket_path)

    def _shutdown(signum, _frame):
        logger.info('signal %s → shutting down', signum)
        try:
            sock.close()
        finally:
            try:
                os.unlink(socket_path)
            except FileNotFoundError:
                pass
            sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            try:
                conn, _addr = sock.accept()
            except OSError:
                # Socket closed during shutdown
                break
            with conn:
                conn.settimeout(120)
                try:
                    chunks = []
                    while True:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        if b'\n' in chunk:
                            break
                    raw = b''.join(chunks).split(b'\n', 1)[0]
                    if not raw:
                        continue
                    reply = handle_request(raw)
                    conn.sendall(reply)
                except socket.timeout:
                    try:
                        conn.sendall(_err('worker read timeout'))
                    except OSError:
                        pass
                except Exception as e:
                    logger.exception('connection handler crashed')
                    try:
                        conn.sendall(_err(f'worker error: {e}'))
                    except OSError:
                        pass
    finally:
        try:
            sock.close()
            os.unlink(socket_path)
        except (OSError, FileNotFoundError):
            pass


def main() -> None:
    logging.basicConfig(
        level=os.getenv('AI_LABEL_REMOTE_LOG_LEVEL', 'INFO'),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    socket_path = os.getenv('AI_LABEL_REMOTE_SOCKET') or SOCKET_PATH_DEFAULT
    serve(socket_path)


if __name__ == '__main__':
    main()
