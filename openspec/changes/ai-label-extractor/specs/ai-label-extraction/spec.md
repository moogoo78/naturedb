## ADDED Requirements

### Requirement: Server-side label extraction endpoint
The application SHALL expose `POST /api/v1/scribe/units/<unit_id>/ai/label` that returns extracted label text for the unit's cover image. The endpoint SHALL accept a JSON body `{ backend: "api" | "remote", image_size: "1024" | "2048" | "4096" (optional, default "2048" for both backends), force: boolean (optional, default false) }` and SHALL return `{ text, model, backend, ms, prompt_version, cached }` on success or `{ error, code }` on failure with appropriate HTTP status.

#### Scenario: Successful API extraction
- **WHEN** an authenticated transcriber POSTs `{ backend: "api" }` for a unit with no cached extraction
- **THEN** the server SHALL fetch the unit's cover image at `image_size`, dispatch to the Anthropic backend, persist the result, and return HTTP 200 with `{ text, model, backend: "api", ms, prompt_version, cached: false }`

#### Scenario: Cache hit returns persisted result
- **WHEN** a transcriber POSTs without `force: true` and a `unit_ai_extraction` row already exists for `(unit_id, prompt_version)`
- **THEN** the server SHALL return the persisted text with `cached: true` and SHALL NOT call any backend

#### Scenario: Forced re-extraction bypasses cache
- **WHEN** a transcriber POSTs with `force: true`
- **THEN** the server SHALL ignore any cached row, call the backend, and overwrite the persisted result

#### Scenario: Unknown unit returns 404
- **WHEN** the path `unit_id` does not exist in the `unit` table
- **THEN** the server SHALL return HTTP 404 with `{ error: "unit not found", code: "not_found" }`

#### Scenario: Unit has no cover image
- **WHEN** the unit exists but `unit.cover_image_id` is null
- **THEN** the server SHALL return HTTP 422 with `{ error: "no cover image", code: "no_image" }`

#### Scenario: Backend failure surfaces to client
- **WHEN** the chosen backend raises (network error, rate limit, worker timeout, etc.)
- **THEN** the server SHALL return HTTP 502 with `{ error: <message>, code: "backend_error", backend, ms }` and SHALL NOT persist a row

### Requirement: Pluggable backend dispatcher
The dispatcher in `app/services/ai/extractor.py` SHALL select between an Anthropic-API backend and a remote-control backend based on the request's `backend` parameter. Each backend SHALL implement the same `extract(image_bytes, *, prompt_version) -> ExtractionResult` interface.

#### Scenario: API backend selected
- **WHEN** `backend == "api"` is passed to `extract_label`
- **THEN** the dispatcher SHALL invoke `anthropic_backend.extract(...)` and SHALL NOT contact the remote worker

#### Scenario: Remote backend selected
- **WHEN** `backend == "remote"` is passed to `extract_label`
- **THEN** the dispatcher SHALL submit a job to the Unix-socket worker and wait up to the configured timeout (default 60s) for the reply

#### Scenario: Unsupported backend rejected
- **WHEN** `backend` is anything other than `"api"` or `"remote"`
- **THEN** the dispatcher SHALL raise `ValueError` and the route SHALL return HTTP 400

### Requirement: Anthropic backend uses prompt caching and inlines image bytes
The Anthropic backend SHALL fetch the image bytes server-side from the cover URL and inline them as base64 in the Messages API request. The system prompt and image content blocks SHALL be marked with `cache_control: { type: "ephemeral" }` so repeat calls for the same image hit Anthropic's prompt cache. The backend SHALL use a vision-capable Claude model (default `claude-sonnet-4-6`) and SHALL request `max_tokens` no higher than 2048.

#### Scenario: Image fetched from S3
- **WHEN** the backend is invoked for a unit with `cover_url = "...-m.jpg"` and `image_size == "2048"`
- **THEN** the backend SHALL request `...-l.jpg` (the URL transformed for size `2048`) and SHALL include the response bytes as a base64 image content block

#### Scenario: Cache breakpoint set on system prompt
- **WHEN** the backend constructs the request to the Messages API
- **THEN** the system prompt block SHALL carry `cache_control: { type: "ephemeral" }`
- **AND** the image content block SHALL also carry `cache_control: { type: "ephemeral" }`

#### Scenario: Prompt version changes invalidate cache
- **WHEN** `PROMPT_VERSION` is bumped from `"label-v1"` to `"label-v2"`
- **THEN** the next call SHALL miss the persisted-row cache (different `prompt_version`) and re-extract

### Requirement: Remote backend communicates over a Unix socket
The remote backend SHALL submit jobs to a long-running local worker over a Unix-domain socket at the path configured by `AI_LABEL_REMOTE_SOCKET`. Submissions SHALL be JSON, one request per connection, with the worker responding with a JSON object on the same connection.

#### Scenario: Worker reachable
- **WHEN** the configured socket exists and the worker accepts connections
- **THEN** the backend SHALL submit `{ unit_id, image_path, prompt_version, model? }` and return the worker's reply

#### Scenario: Worker unreachable
- **WHEN** the socket file is missing or `connect()` raises `ConnectionRefusedError`
- **THEN** the backend SHALL raise `RemoteUnavailable` and the route SHALL return HTTP 503 with `{ error: "remote backend unavailable", code: "remote_down" }`

#### Scenario: Worker timeout
- **WHEN** the worker accepts but does not reply within the configured timeout (default 60s)
- **THEN** the backend SHALL close the connection, raise `RemoteTimeout`, and the route SHALL return HTTP 504

### Requirement: Per-unit extraction persistence
The application SHALL persist each extraction as an append-only row in the existing `unit_verbatim` table with `source_type = 'ai'` and `section_type = 'full'`. AI metadata (backend, model, prompt_version, image_size, ms) SHALL be stored in `source_data` JSONB. The "current" extraction for a unit at the active prompt version is the most-recently-created matching row.

#### Scenario: Insert on every extraction
- **WHEN** the dispatcher receives a backend reply
- **THEN** the dispatcher SHALL insert a new `UnitVerbatim` row with `source_type='ai'`, `section_type='full'`, `text=<reply.text>`, and `source_data={backend, model, prompt_version, image_size, ms}`

#### Scenario: Cache lookup returns latest row at active prompt version
- **WHEN** an extraction is requested with `force=false` and at least one `UnitVerbatim` row exists with `source_type='ai'` and `source_data->>'prompt_version'` matching the active version
- **THEN** the dispatcher SHALL return the most recent matching row's text and metadata with `cached=True`

#### Scenario: Force inserts a new row even when cached row exists
- **WHEN** `force=true` is set
- **THEN** the dispatcher SHALL ignore any cached row and insert a fresh `UnitVerbatim` row; both rows SHALL coexist (append-only, no overwrite)

#### Scenario: Different prompt_version is independent
- **WHEN** an extraction is requested at `prompt_version="label-v2"` and rows exist at `"label-v1"`
- **THEN** the v1 rows SHALL be ignored by the cache lookup and a new v2 row SHALL be inserted

### Requirement: Extraction summary surfaced in specimens API
`GET /api/v1/scribe/specimens` (the existing list endpoint) SHALL include a per-specimen `ai_extraction` field summarising the latest extraction at the current prompt version: `{ text, model, backend, ms, created_at } | null`.

#### Scenario: Specimen with extraction
- **WHEN** a unit has an `unit_ai_extraction` row at the active `PROMPT_VERSION`
- **THEN** the specimen item in the API response SHALL include `ai_extraction: { text, model, backend, ms, created_at }`

#### Scenario: Specimen without extraction
- **WHEN** a unit has no row at the active `PROMPT_VERSION`
- **THEN** the specimen item SHALL include `ai_extraction: null`

### Requirement: Per-user rate limiting
The endpoint SHALL enforce a per-user rate limit on un-cached calls (default 60 per hour per user). Cached responses SHALL NOT count against the limit.

#### Scenario: Within limit
- **WHEN** a user has made fewer than the configured number of un-cached calls in the past hour
- **THEN** the endpoint SHALL accept the request

#### Scenario: Limit exceeded
- **WHEN** a user has hit the limit
- **THEN** the endpoint SHALL return HTTP 429 with `{ error: "rate limit exceeded", code: "rate_limit", retry_after }`
