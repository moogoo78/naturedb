## 1. Schema & migration

- [x] 1.1 Add `Person.preferences_json` JSONB column to the Person model with `server_default='{}'`; create alembic migration
- [x] 1.2 ~~Create UnitAiExtraction model~~ — superseded: reuse existing `UnitVerbatim` (source_type='ai'). See design.md §4
- [x] 1.3 ~~Generate alembic migration for unit_ai_extraction table~~ — superseded; only Person migration remains
- [x] 1.4 Add functional index `ix_unit_verbatim_ai_prompt_version` on `unit_verbatim(unit_id, source_type, (source_data->>'prompt_version'))` for fast cache lookup; include in the same Person-prefs migration

## 2. Backend dispatcher & API backend

- [x] 2.1 Create `app/services/ai/__init__.py` and `app/services/ai/extractor.py` with `ExtractionResult` dataclass and `extract_label(unit, *, backend, image_size, force, model=None) -> ExtractionResult`
- [x] 2.2 Define backend interface (`extract(image_bytes, *, prompt_version, model) -> ExtractionResult`) and the constants `PROMPT_VERSION = "label-v1"`, `LABEL_SYSTEM_PROMPT`
- [x] 2.3 Implement `app/services/ai/anthropic_backend.py`: fetch image bytes from S3 cover URL, base64-inline, call Anthropic Messages API with `cache_control: ephemeral` on system prompt and image block, default model `claude-sonnet-4-6`, `max_tokens=2048`
- [x] 2.4 Add `anthropic==0.97.0` (exact-version pin) to `requirements.txt`
- [x] 2.5 Add env vars to `app/config.py`: `ANTHROPIC_API_KEY`, `AI_LABEL_DEFAULT_BACKEND`, `AI_LABEL_REMOTE_SOCKET`, `AI_LABEL_REMOTE_TIMEOUT`, `FEATURE_AI_LABEL`, `AI_LABEL_RATE_PER_HOUR`
- [x] 2.6 Implement cache lookup in dispatcher: if a `UnitVerbatim` row exists with `source_type='ai'` and `source_data->>'prompt_version'` matching `PROMPT_VERSION` and `force` is false, return the most recent one with `cached=True`
- [x] 2.7 Implement append-on-success: insert a new `UnitVerbatim` row with `source_type='ai'`, `section_type='full'`, `user_id=current_user.id`, and AI metadata in `source_data`

## 3. Remote backend & worker

- [x] 3.1 Implement `app/services/ai/remote_backend.py`: connect to `AI_LABEL_REMOTE_SOCKET`, send JSON request, await JSON reply with timeout, raise `BackendUnavailable` / `BackendTimeout` on failure
- [x] 3.2 Scaffold `app/services/ai/remote_worker.py`: long-running process listening on the socket, with a stub `_call_claude(image_bytes, prompt_version, model)` extension point and graceful SIGINT/SIGTERM shutdown
- [x] 3.3 Worker docs added at `docs/ai-label-remote-worker.md` with protocol, env vars, systemd unit example, and three bridge implementation patterns (subprocess / Agent SDK / MCP)
- [x] 3.4 Implement worker health-check: `GET /api/v1/scribe/ai/health` returns `{ remote_available: bool }` by attempting a non-blocking socket connect

## 4. Flask route

- [x] 4.1 Add `POST /api/v1/scribe/units/<unit_id>/ai/label` to `app/blueprints/api.py`; gated by `@login_required` (Flask-Login); validate JSON body
- [x] 4.2 Map exceptions → HTTP codes per `ai-label-extraction` spec: `not_found` → 404, `no_image` → 422, `remote_down` → 503, `remote_timeout` → 504, `backend_error` → 502, `rate_limit` → 429
- [x] 4.3 Implement per-user rate limiting (default 60 un-cached calls/hour) — simple in-memory counter `_AI_LABEL_BUCKETS` keyed by `(user_id, hour_bucket)`
- [x] 4.4 Hide route behind `FEATURE_AI_LABEL` flag (returns 404 when disabled)

## 5. Specimen list payload

- [x] 5.1 In `app/exporters/scribe.py`, add `fetch_ai_extractions(unit_ids, prompt_version)` returning `{ unit_id: extraction_dict | None }` via a single windowed `SELECT`
- [x] 5.2 Wire `ai_extraction` into each item dict in `shape_specimens_page`
- [ ] 5.3 Verify `GET /api/v1/scribe/specimens` response includes the new field — needs runtime check after migration applied

## 6. Frontend i18n & state

- [x] 6.1 Add zh strings to `app/static/js/annotate/i18n.js`: panel title (AI 標籤辨識), backend labels (Anthropic API / 遠端 Claude session), Read label (讀取標籤), Re-read (重新讀取), AI draft warning (AI 草稿 — 使用前請確認), confirmation copy, error messages
- [x] 6.2 Add `aiState` to the modal-level state struct in `annotation.js`: `{ backend, draftText, history: [], inflight: bool, error: null }` — implemented via `makeAiState(specimen)` in ai_panel.js and stored on `modalState.aiState`

## 7. Frontend AI panel

- [x] 7.1 Create `app/static/js/annotate/ai_panel.js` with `renderAiPanel(specimen, aiState)` and `attachAiPanelEvents(host, specimen, aiState, rerenderPanel)` exports
- [x] 7.2 Render the panel inside `image-rail` between "Specimen plate" and "Recent annotators" (modified `renderImageRail` in `annotation.js`)
- [x] 7.3 Backend selector `<select>` reads/writes `aiState.backend` and persists to `localStorage["ai_label_backend"]`
- [x] 7.4 Read label button → POST `/ai/label`, populate textarea on success, show inline error on failure, append history entry
- [x] 7.5 Re-read button → POST with `force: true`; on `backend == "api"` AND `draftText` present, shows confirmation dialog first
- [x] 7.6 ~~Server-side preferences endpoint~~ — deferred to v1.1
- [x] 7.7 Hydrate `aiState.draftText` from `specimen.ai_extraction.text` on modal open (and rebuild on Prev/Next navigation when specimen.id changes)
- [x] 7.8 Disable Remote option when `/ai/health` reports `remote_available: false` (cached promise, fetched once per page)

## 8. Styling

- [x] 8.1 Added CSS for `.ai-panel`, `.ai-backend-select`, `.ai-read-btn`, `.ai-reread-btn`, `.ai-draft-textarea`, `.ai-history`, `.ai-error-banner`, `.ai-initial-meta` to `app/static/css/annotate.css`
- [x] 8.2 Matches existing rail-section visual style; textarea uses mono font + paper-2 background tint to distinguish from form fields

## 9. Tests

- [x] 9.1 Unit test: dispatcher returns cached row when present and `force=false` → `tests/test_ai_extractor.py::test_dispatcher_returns_cached_row_when_present`
- [x] 9.2 Unit test: dispatcher appends new row on `force=true` (revised from "upserts" — UnitVerbatim is append-only) → `test_dispatcher_force_appends_new_row`
- [x] 9.3 Unit test: dispatcher raises on unsupported backend → `test_dispatcher_rejects_unknown_backend`
- [x] 9.4 Unit test: API backend constructs the Messages API payload with cache_control on system + image blocks → `test_anthropic_backend_payload_has_cache_control`
- [x] 9.5 Unit test: remote backend raises `BackendUnavailable` when socket is missing → `test_remote_backend_missing_socket_raises_unavailable` (+ `test_remote_backend_round_trip_via_real_socket` and `test_remote_backend_worker_returns_error` for happy path and error reply)
- [x] 9.6 Integration test: `POST /ai/label` happy path + exception mapping (404 unknown unit, 400 bad backend/size, 422 no_image, 502/503/504 backend errors) → `tests/test_ai_route.py`
- [x] 9.7 Integration test: rate limit returns 429 after N+1 un-cached calls; cached calls don't consume bucket → `test_route_returns_429_after_limit`, `test_route_cached_result_does_not_consume_rate_limit`
- [x] 9.8 Unit test: `fetch_ai_extractions` shape (single windowed query → per-unit dict) → `test_fetch_ai_extractions_shape`, `test_fetch_ai_extractions_empty_input`

## 10. Rollout

- [ ] 10.1 Deploy with `FEATURE_AI_LABEL=false`, confirm no regressions in existing transcription flow
- [ ] 10.2 Set `FEATURE_AI_LABEL=true` for moogoo's account only via a `Person.preferences_json` override and verify panel renders + both backends work
- [ ] 10.3 Document remote-worker startup in repo README + add a systemd unit example under `docs/`
- [ ] 10.4 After two weeks of internal usage, decide whether to flip the default backend (`AI_LABEL_DEFAULT_BACKEND`) and whether to enable the feature project-wide
