"""Anthropic API backend: Messages API with vision input + prompt caching."""
from __future__ import annotations

import base64
import os
import time
from typing import Optional

from app.services.ai.extractor import (
    BackendError,
    ExtractionResult,
    LABEL_SYSTEM_PROMPT,
    PROMPT_VERSION,
)


DEFAULT_MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 2048


def extract(
    image_bytes: bytes,
    *,
    prompt_version: str = PROMPT_VERSION,
    model: Optional[str] = None,
) -> ExtractionResult:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise BackendError('ANTHROPIC_API_KEY not configured')

    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise BackendError(f'anthropic SDK not installed: {e}')

    client = Anthropic(api_key=api_key)
    use_model = model or DEFAULT_MODEL

    started = time.monotonic()
    try:
        msg = client.messages.create(
            model=use_model,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    'type': 'text',
                    'text': LABEL_SYSTEM_PROMPT,
                    'cache_control': {'type': 'ephemeral'},
                }
            ],
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': base64.b64encode(image_bytes).decode('ascii'),
                            },
                            'cache_control': {'type': 'ephemeral'},
                        },
                        {
                            'type': 'text',
                            'text': 'Transcribe this label.',
                        },
                    ],
                }
            ],
        )
    except Exception as e:
        raise BackendError(f'Anthropic API call failed: {e}') from e

    ms = int((time.monotonic() - started) * 1000)

    # Concatenate all text blocks in the reply
    parts = [b.text for b in msg.content if getattr(b, 'type', None) == 'text']
    text = '\n'.join(parts).strip()
    if not text:
        raise BackendError('Anthropic returned no text content')

    return ExtractionResult(
        text=text,
        model=use_model,
        backend='api',
        ms=ms,
        prompt_version=prompt_version,
    )
