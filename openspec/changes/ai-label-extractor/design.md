## Context

The transcription page (`/annotate` modal, served by `app/templates/annotate/index.html` + `app/static/js/annotate/`) shows a high-resolution specimen image on the left and an editable form on the right. Cover URLs are S3 paths with `-s/-m/-l/-o.jpg` size suffixes (1024 / 2048 / 4096 px tiers). The form state is structured (collector, date, locality, geospatial, identifications…), but the *source of truth* on the image is unstructured human-written text.

Multimodal LLMs (Anthropic's Claude in particular) can transcribe both typed and handwritten label text directly from an image input. We have two delivery paths under consideration:

1. **Direct API** — server-to-server call to `https://api.anthropic.com/v1/messages` with a vision-capable model (`claude-sonnet-4-6`). Predictable, billable, low-latency, and auditable.
2. **Remote-control** — a thin worker that bridges the running operator's Claude Code session (the operator is moogoo, working on this very feature). Re-uses the operator's existing Claude subscription rather than incurring per-call API costs, but adds an extra hop and a session-availability dependency.

Stakeholders are: transcribers (UX), the project owner (cost & deployment), and downstream curators (data quality of suggestions). Existing transcription work (tasks #1–#7 of this session) added the multi-identification UI and a save endpoint, so this change slots in *next to* the form, not into it.

## Goals / Non-Goals

**Goals:**
- Reduce the time-to-first-draft of a specimen label from "minutes typing" to "seconds verifying".
- Keep the AI suggestion strictly *advisory*: never auto-fill a structured field in this change.
- Make backend choice (API vs Remote) a runtime toggle, not a build-time flag — so we can A/B compare quality and latency without redeploying.
- Cache extracted text per `(unit_id, image_size, model, prompt_version)` so re-opening the modal is free.
- Surface call cost / latency in the UI so transcribers and the operator can see the price of each attempt.

**Non-Goals:**
- Field-level AI suggestions (Suggest button per field) — separate future change. This delivers only the raw-text "draft pool".
- Any auto-submission, auto-saving, or auto-population of identifications. The pool is read-only-source for the human.
- A general AI gateway. The dispatcher is scoped to label extraction; if we later add other AI tasks (taxon validation, locality geocoding) they should reuse the dispatcher pattern but live in their own modules.
- Multi-image support (composing front + back of label). Single cover image only in v1.

## Decisions

### 1. Backend dispatcher lives in `app/services/ai/`

A new `app/services/ai/extractor.py` defines a single `extract_label(unit, *, backend, image_size="2048", model=None) -> ExtractionResult` function. Internally dispatches to `anthropic_backend.py` or `remote_backend.py`. Returns a dataclass: `text, model, backend, ms, prompt_version, cached, error`.

**Why this shape**: it isolates HTTP/SDK details from Flask routes, makes both backends trivially mockable in tests, and keeps the cache lookup in one place (the dispatcher checks `UnitAiExtraction` before calling either backend).

**Alternative rejected**: doing the dispatch inside the Flask route. Tempting for a small feature, but the remote backend's enqueue/poll logic is non-trivial and bleeding it into request handlers makes both harder to test.

### 2. API backend uses prompt caching

The system prompt + the image (when image-size is the same) is sent with `cache_control: ephemeral` so repeat reads of the same image (different prompt tweaks) hit the prompt cache. Image bytes are fetched server-side from S3 (don't send the URL — Anthropic doesn't fetch by URL) and inlined as base64.

The herbarium-label prompt (v1) targets *raw transcription only*: "Read every legible character on the label, preserving line breaks and original spelling. Do not interpret, translate, or restructure. Mark unreadable runs with `[…]`." Prompt is versioned (`PROMPT_VERSION = "label-v1"`) so cache can invalidate when we tune it.

**Why prompt caching**: even at the smallest size tier (1024px) a label image is ~80–150 KB base64. Without caching, every "Re-read" click pays full input cost. With caching, only the (small) prompt-suffix and output are billed.

### 3. Remote backend uses a Unix-socket queue

A long-running local worker (`app/services/ai/remote_worker.py`, started as a separate process) listens on a Unix socket. Flask submits `{ unit_id, image_path, prompt_version }`, waits up to 60s for a reply (`{ text, model, ms }` or `{ error }`). Inside the worker, the bridge to Claude Code is intentionally *out of this change's scope* — the worker exposes a stable JSON-over-socket API; how it actually drives Claude is a separate piece (and may evolve from "headless CLI invocation" to "MCP client" without touching this code).

**Why a separate process**: gunicorn workers shouldn't hold long-lived stdio handles to Claude. A single worker also de-duplicates concurrent requests for the same unit.

**Why Unix socket** (not HTTP): zero auth surface (file permissions only), zero network exposure, no port management. Same machine deployment is the only supported topology in v1.

**Alternative rejected**: shelling out to `claude` CLI from inside the request. Blocks a gunicorn worker for 10–30s per call and breaks under any concurrency.

### 4. Result persistence: reuse `UnitVerbatim` (`source_type='ai'`)

The codebase already has `UnitVerbatim` (`app/models/collection.py:2548`), purpose-built for multi-source label transcriptions. It defines `SOURCE_AI = 'ai'`, `SECTION_FULL = 'full'`, and a `source_data` JSONB column documented for AI metadata (`{model, prompt, cost_usd, ...}`). Reusing it avoids splitting AI transcriptions across two tables and matches the existing `Unit.verbatim_transcriptions` relationship.

Each extraction inserts a row:
```python
UnitVerbatim(
  unit_id=unit.id,
  user_id=current_user.id,
  text=extraction.text,
  section_type='full',
  source_type='ai',
  source_data={
    'backend': 'api' | 'remote',
    'model': 'claude-sonnet-4-6',
    'prompt_version': 'label-v1',
    'image_size': '2048',
    'ms': 1234,
  },
)
```

"Latest extraction at active prompt version" is computed as:
```python
UnitVerbatim.query.filter(
    UnitVerbatim.unit_id == unit.id,
    UnitVerbatim.source_type == 'ai',
    UnitVerbatim.source_data['prompt_version'].astext == PROMPT_VERSION,
).order_by(UnitVerbatim.created.desc()).first()
```

A small functional index `(unit_id, source_type, (source_data->>'prompt_version'))` keeps the lookup fast as the table grows. Append-only is now the model — every AI attempt is preserved, which matches the existing `UnitVerbatim` design intent and gives us a free history surface in v1.1 without re-architecting.

**Alternative rejected**: a new `unit_ai_extraction` table. Cleaner unique constraint per `(unit, prompt_version)`, but duplicates schema and forces every reader/exporter to query two places. Reusing `UnitVerbatim` is strictly better given it already exists.

### 5. UI: AI panel embedded in `image-rail`, not the form panel

The existing right-side `image-rail` (under the image) has two sections: "Specimen plate" thumbnails and "Recent annotators". We add a third section: "AI label reader". This keeps the AI suggestion visually adjacent to the *image* (the source it's reading), not the *form* (the target it's not auto-filling). The form panel stays untouched in this change.

**Why not a modal/drawer**: transcribers need to look at the image, the AI text, *and* type into the form simultaneously. Three columns of context, not stacked surfaces.

### 6. Backend toggle: per-user setting persisted on `Person` (or session)

A small `<select>` in the AI panel header switches `api ↔ remote`. Selection is sent with each call (the server doesn't trust client identity for billing decisions, but the toggle reflects user intent for UX). Default comes from `AI_LABEL_DEFAULT_BACKEND` env var. Persisted in `Person.preferences_json` (a new JSONB column) so it survives sessions; if a transcriber isn't logged in, falls back to `localStorage`.

**Alternative rejected**: a project-wide setting. Reduces user agency and makes A/B comparison harder during the evaluation period.

## Risks / Trade-offs

- **[Cost runaway]** A bored transcriber clicking "Re-read" 50 times on the largest image tier could rack up real money. → Mitigation: per-(unit, prompt_version) cache means re-reads on the same parameters are free; explicit confirm modal on backend=api when the cached result already exists; rate-limit `/ai/label` to N requests per hour per user.
- **[Remote backend availability]** Operator's Claude Code session can be down. → Mitigation: worker health-check endpoint; UI disables the Remote option (with tooltip explaining why) when the socket is unreachable; never auto-fallback to API without explicit user opt-in (would hide cost).
- **[Hallucination on illegible labels]** LLM may fabricate plausible-looking text rather than mark `[…]`. → Mitigation: prompt-engineered to use `[…]` for illegible runs; UI labels the textarea "AI draft — verify before using"; in-session history shows multiple attempts so the transcriber can compare.
- **[Image fetch from S3 inside request]** Latency + bandwidth cost on the Flask host. → Mitigation: smallest tier (1024px) is the default; image fetch is cached in-process for the duration of the request; consider moving to a signed URL + Anthropic-side fetch if/when their API supports it.
- **[Remote-control auth model is undefined]** This change's scope ends at the Unix socket. The worker's connection to Claude Code is a separate trust boundary. → Mitigation: explicitly call out in the worker's docstring; add a warning to the operator install path; defer hardening until we have actual usage signal.
- **[PII / sensitive data in label]** Some labels contain collector names, GPS coordinates, etc. Sending to Anthropic (API backend) is a data-egress event. → Mitigation: document this in user-facing copy ("API backend sends image to Anthropic; Remote backend keeps it on this machine"); make Remote the default in the env var.

## Migration Plan

1. Ship the `unit_ai_extraction` table migration in a separate small alembic revision (or whatever migration mechanism is in use — check `app/database.py` during apply).
2. Land the dispatcher + Anthropic backend first, behind a `FEATURE_AI_LABEL=false` env flag (UI does not render the panel). Verify in staging.
3. Land the UI panel; flip flag to `true` for moogoo's account only via a `Person.preferences_json` override.
4. Land the remote backend + worker; toggle becomes user-visible.
5. After two weeks of usage, evaluate cost, latency, and quality data; decide whether to make Remote or API the project-wide default.

Rollback: flip `FEATURE_AI_LABEL=false`. The `unit_ai_extraction` rows can stay; nothing else reads them.

## Resolved Decisions (post-grill)

- **Anthropic SDK pin**: pin to an exact version (`anthropic==<latest-stable-at-install>`) in `requirements.txt`. Bump intentionally in a follow-up commit when we want to track a new SDK release. Avoids silent breakage from upstream changes to argument names or response shape.
- **Image-size default**: `2048` for both backends. Larger tier produces materially better handwriting reads; cost difference is bounded by per-(unit, prompt_version) caching.
- **Cumulative session cost in UI**: out of scope for v1. The per-call history already surfaces latency, model, and cached/uncached — that's enough for cost awareness without threading token counts through every layer. Revisit in v1.1 if usage signal demands it.
- **`Person.preferences_json` column**: add it as a new JSONB column in this change's migration so each user can store and update their own backend preference (and any future per-user settings). Default `{}`.
