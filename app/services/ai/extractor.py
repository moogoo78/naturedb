"""Dispatcher for AI label extraction on the transcription page.

Reads the unit's cover image, dispatches to one of two backends (Anthropic API
or local remote-control worker), and persists the result as a UnitVerbatim row
with source_type='ai'. See openspec/changes/ai-label-extractor/design.md.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import desc

from app.database import session
from app.models.collection import Unit, UnitVerbatim


PROMPT_VERSION = 'label-v1'

LABEL_SYSTEM_PROMPT = (
    "You are reading a herbarium specimen label from a photograph. "
    "Transcribe every legible character on the label exactly as written, "
    "preserving line breaks and original spelling. "
    "Do not interpret, translate, restructure, or summarise. "
    "Mark unreadable runs with [...]. "
    "Output only the raw label text, nothing else."
)


@dataclass
class ExtractionResult:
    text: str
    model: str
    backend: str             # 'api' | 'remote'
    ms: int
    prompt_version: str = PROMPT_VERSION
    image_size: str = '2048'
    cached: bool = False
    verbatim_id: Optional[int] = None


class BackendError(Exception):
    """Backend produced an error reply (network, rate limit, etc.)."""


class BackendUnavailable(BackendError):
    """Backend is down or unreachable (e.g. remote worker socket missing)."""


class BackendTimeout(BackendError):
    """Backend accepted but failed to reply within the configured timeout."""


class NoCoverImage(Exception):
    """Unit has no cover_image_id, can't extract."""


def _latest_cached(unit_id: int):
    return (
        session.query(UnitVerbatim)
        .filter(
            UnitVerbatim.unit_id == unit_id,
            UnitVerbatim.source_type == UnitVerbatim.SOURCE_AI,
            UnitVerbatim.source_data['prompt_version'].astext == PROMPT_VERSION,
        )
        .order_by(desc(UnitVerbatim.created))
        .first()
    )


def _persist(unit_id: int, user_id: Optional[int], result: ExtractionResult) -> int:
    row = UnitVerbatim(
        unit_id=unit_id,
        user_id=user_id,
        text=result.text,
        section_type=UnitVerbatim.SECTION_FULL,
        source_type=UnitVerbatim.SOURCE_AI,
        source_data={
            'backend': result.backend,
            'model': result.model,
            'prompt_version': result.prompt_version,
            'image_size': result.image_size,
            'ms': result.ms,
        },
    )
    session.add(row)
    session.flush()  # populate row.id without committing
    return row.id


def _fetch_cover_image_bytes(unit: Unit, image_size: str) -> bytes:
    """Fetch the unit's cover image at the requested size suffix.

    The cover URL pattern is `...-{s|m|l|o}.jpg`; size labels map to suffixes
    s=512, m=1024, l=2048, o=original. We always rewrite to `-l.jpg` for
    image_size='2048'; '1024' uses '-m.jpg'; '4096' uses '-o.jpg'.
    """
    import requests

    cover = unit.cover_image
    if cover is None or not cover.file_url:
        raise NoCoverImage(f'unit {unit.id} has no cover image')

    suffix = {'1024': 'm', '2048': 'l', '4096': 'o'}.get(image_size, 'l')
    url = cover.file_url
    # Replace any of -s/-m/-l/-o.jpg with the requested suffix
    import re
    url = re.sub(r'-[smlo]\.jpg$', f'-{suffix}.jpg', url, flags=re.IGNORECASE)

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def extract_label(
    unit: Unit,
    *,
    backend: str,
    image_size: str = '2048',
    force: bool = False,
    model: Optional[str] = None,
    user_id: Optional[int] = None,
) -> ExtractionResult:
    """Top-level dispatcher used by the Flask route.

    Returns an ExtractionResult. Raises NoCoverImage / BackendError /
    BackendUnavailable / BackendTimeout / ValueError for the route to map
    to HTTP codes.
    """
    if backend not in ('api', 'remote'):
        raise ValueError(f'unsupported backend: {backend!r}')

    # Cache lookup
    if not force:
        cached_row = _latest_cached(unit.id)
        if cached_row is not None:
            sd = cached_row.source_data or {}
            return ExtractionResult(
                text=cached_row.text,
                model=sd.get('model', ''),
                backend=sd.get('backend', backend),
                ms=int(sd.get('ms', 0)),
                prompt_version=PROMPT_VERSION,
                image_size=sd.get('image_size', image_size),
                cached=True,
                verbatim_id=cached_row.id,
            )

    # Fetch image (raises NoCoverImage)
    image_bytes = _fetch_cover_image_bytes(unit, image_size)

    # Dispatch
    started = time.monotonic()
    if backend == 'api':
        from app.services.ai.anthropic_backend import extract as backend_extract
    else:  # remote
        from app.services.ai.remote_backend import extract as backend_extract

    result = backend_extract(
        image_bytes,
        prompt_version=PROMPT_VERSION,
        model=model,
    )
    # Backends should set ms themselves, but we backstop here
    if not result.ms:
        result.ms = int((time.monotonic() - started) * 1000)
    result.image_size = image_size

    # Persist
    verbatim_id = _persist(unit.id, user_id, result)
    result.verbatim_id = verbatim_id
    return result
