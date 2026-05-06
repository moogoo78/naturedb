## Why

Transcribers on the Nature-Scribe transcription page (`/annotate` modal) currently re-type every specimen label by hand from the high-resolution image. Modern multimodal LLMs can read both typed and handwritten herbarium labels with high accuracy, so an AI-assist that pre-fills a draft text pool would let transcribers shift from typing to verification — a much faster and lower-friction loop. Adding this now also lets us evaluate two delivery paths in parallel (direct Anthropic API vs. routing through the operator's Claude Code session), which informs longer-term cost and deployment decisions before we wire the AI suggestions into individual fields.

## What Changes

- Add an "AI label reader" panel to the transcription view (image pane) with: a **Read label** action button, a backend selector (API ↔ Claude remote-control), a **Draft pool** textarea showing the raw extracted text, and per-attempt history (status, model, latency, token cost).
- New Flask endpoint `POST /api/v1/scribe/units/<unit_id>/ai/label` that returns `{ text, model, backend, ms, error? }`. The endpoint dispatches to one of two backends:
  - **API backend**: calls Anthropic's Messages API with the specimen image as a vision input and a herbarium-label-extraction prompt; cached by `unit_id` + image-resolution + model + prompt-hash.
  - **Remote backend**: enqueues a job to a local "remote-control" worker that drives the operator's Claude Code session over an authenticated channel, returning the same shape.
- Add a backend-selection setting (per-user, with project default) so individual transcribers can choose API or Remote.
- Persist the latest extraction result on the `Unit` (or in a sibling `unit_ai_extraction` table) so re-opening the modal doesn't re-bill calls.
- The draft pool is **read-only suggestion** — does not auto-fill any field. A future change will wire pool text into individual field "Suggest" actions; this change just produces and shows the pool.

## Capabilities

### New Capabilities
- `ai-label-extraction`: server-side dispatch to a multimodal LLM that turns a specimen image into raw label text, with pluggable backend and per-unit caching.
- `transcription-ai-panel`: the AI-helper UI surface inside the transcription modal — backend toggle, action button, draft pool textarea, history list.

### Modified Capabilities
- `annotation-explorer`: the transcription modal now embeds the AI panel; specimen detail payload gains an `ai_extraction` summary so the panel can hydrate without a second round-trip.

## Impact

- **Code**:
  - `app/blueprints/api.py` — new `/scribe/units/<id>/ai/label` route + backend dispatcher.
  - `app/exporters/scribe.py` — include latest `ai_extraction` in `shape_specimens_page`.
  - `app/services/ai/` (new) — `extractor.py` (interface), `anthropic_backend.py`, `remote_backend.py`.
  - `app/models/collection.py` (or new `app/models/ai.py`) — new `UnitAiExtraction` model + migration.
  - `app/static/js/annotate/annotation.js` — render AI panel inside `image-rail`, wire actions.
  - `app/static/css/annotate.css` — panel styling.
  - `app/static/js/annotate/i18n.js` — zh strings.
- **Dependencies**: add `anthropic` Python SDK (already a likely candidate). The remote-control backend assumes an existing local channel/socket — out-of-scope sub-design lives in `design.md`.
- **Config**: new env vars `ANTHROPIC_API_KEY`, `AI_LABEL_DEFAULT_BACKEND` (`api`|`remote`), `AI_LABEL_REMOTE_ENDPOINT`.
- **Cost / risk**: outbound LLM calls are billable; per-unit caching plus an explicit user-triggered button keep usage bounded. Image is sent to Anthropic only when API backend is selected — the choice is auditable per call.
- **Security**: API key lives only in the server process; the browser never sees it. Remote-control channel authentication is its own auth surface — design.md must address it.
