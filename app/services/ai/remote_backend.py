"""Remote-control backend: Unix-socket bridge to the operator's Claude session.

This module ONLY speaks to a local worker over a Unix-domain socket. The
worker itself (and its bridge to a Claude Code session) is out of scope for
this change — see openspec/changes/ai-label-extractor/design.md decision §3.

A scaffold worker is provided in app/services/ai/remote_worker.py.
"""
from __future__ import annotations

import json
import os
import socket
import time
from typing import Optional

from app.services.ai.extractor import (
    BackendError,
    BackendTimeout,
    BackendUnavailable,
    ExtractionResult,
    PROMPT_VERSION,
)


def _socket_path() -> str:
    return os.getenv('AI_LABEL_REMOTE_SOCKET') or '/tmp/naturedb-ai-label.sock'


def _timeout_seconds() -> float:
    try:
        return float(os.getenv('AI_LABEL_REMOTE_TIMEOUT', '60'))
    except ValueError:
        return 60.0


def extract(
    image_bytes: bytes,
    *,
    prompt_version: str = PROMPT_VERSION,
    model: Optional[str] = None,
) -> ExtractionResult:
    path = _socket_path()
    timeout = _timeout_seconds()

    if not os.path.exists(path):
        raise BackendUnavailable(f'remote worker socket not found: {path}')

    started = time.monotonic()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(path)
    except (ConnectionRefusedError, FileNotFoundError) as e:
        raise BackendUnavailable(f'cannot connect to remote worker: {e}') from e

    try:
        # Inline the image as base64 in the request so the worker doesn't
        # need filesystem access to the same path.
        import base64
        request = {
            'image_b64': base64.b64encode(image_bytes).decode('ascii'),
            'prompt_version': prompt_version,
            'model': model,
        }
        sock.sendall(json.dumps(request).encode('utf-8') + b'\n')

        chunks = []
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout as e:
                raise BackendTimeout(f'remote worker did not reply within {timeout}s') from e
            if not chunk:
                break
            chunks.append(chunk)
            if b'\n' in chunk:
                break
    finally:
        sock.close()

    raw = b''.join(chunks).strip()
    if not raw:
        raise BackendError('remote worker returned empty reply')

    try:
        reply = json.loads(raw.split(b'\n', 1)[0])
    except json.JSONDecodeError as e:
        raise BackendError(f'remote worker reply is not JSON: {e}') from e

    if 'error' in reply:
        raise BackendError(f'remote worker reported: {reply["error"]}')

    ms = int((time.monotonic() - started) * 1000)
    return ExtractionResult(
        text=reply.get('text', ''),
        model=reply.get('model', model or 'remote'),
        backend='remote',
        ms=ms,
        prompt_version=prompt_version,
    )
