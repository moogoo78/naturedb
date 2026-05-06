## ADDED Requirements

### Requirement: AI label reader panel embedded in image rail
The transcription modal SHALL render an "AI label reader" section inside the existing right-side `image-rail` (between "Specimen plate" and "Recent annotators"). The section SHALL contain a backend selector, a primary action button, a draft-pool textarea, and a per-session attempt history.

#### Scenario: Panel renders on modal open
- **WHEN** a transcriber opens the transcription modal for any specimen
- **THEN** the AI label reader section SHALL be visible in the image rail with the backend selector defaulting to the user's saved preference (or `AI_LABEL_DEFAULT_BACKEND` if none)

#### Scenario: Panel hidden when feature disabled
- **WHEN** the `FEATURE_AI_LABEL` env flag is `false`
- **THEN** the section SHALL NOT render and the JS module SHALL NOT call `/ai/label`

### Requirement: Backend selector
The panel SHALL render a `<select>` (or equivalent toggle) with two options labelled "Anthropic API" and "Remote (Claude session)". Selection SHALL be persisted to the user's preferences (`Person.preferences_json.ai_label_backend`) and SHALL be sent with each `/ai/label` request.

#### Scenario: Default selection
- **WHEN** the panel renders for a user with no saved preference
- **THEN** the selector SHALL be set to the value of `AI_LABEL_DEFAULT_BACKEND`

#### Scenario: Selection persists across sessions
- **WHEN** a transcriber changes the selector from "API" to "Remote"
- **THEN** the change SHALL be POSTed to `/api/v1/people/me/preferences` (or equivalent existing preference endpoint) and SHALL be the default the next time the modal opens

#### Scenario: Remote disabled when worker unreachable
- **WHEN** the page boot-up health check reports the remote worker is down
- **THEN** the "Remote (Claude session)" option SHALL be disabled with a tooltip explaining the worker is unreachable

### Requirement: Read label action
The panel SHALL render a primary button labelled "Read label" (zh: 讀取標籤). Clicking SHALL POST to `/api/v1/scribe/units/<unit_id>/ai/label` with the current backend selection. While the request is in flight the button SHALL show a spinner and the textarea SHALL be marked busy.

#### Scenario: Successful read populates textarea
- **WHEN** the API responds 200 with `{ text, model, backend, ms, cached }`
- **THEN** the textarea SHALL show `text`, the history list SHALL gain an entry `{ backend, model, ms, cached, at }`, and the button SHALL re-enable

#### Scenario: Cached response indicated in UI
- **WHEN** the response includes `cached: true`
- **THEN** the textarea SHALL display the text and the history entry SHALL be tagged "cached" (no cost)

#### Scenario: Failure shows inline error
- **WHEN** the API responds with non-2xx
- **THEN** the panel SHALL show an inline error banner with the `error` message, the textarea SHALL preserve any prior text, and the button SHALL re-enable

### Requirement: Re-read action with cost confirmation
The panel SHALL provide a secondary "Re-read" affordance that POSTs with `force: true`. When the current backend is `"api"` and a cached row exists, clicking SHALL show a confirmation modal explaining the call will be re-billed before submitting.

#### Scenario: Re-read on remote backend skips confirmation
- **WHEN** the backend selector is "Remote" and the user clicks Re-read
- **THEN** the confirmation modal SHALL NOT appear and the request SHALL be sent immediately

#### Scenario: Re-read on API backend with cache shows confirmation
- **WHEN** the backend is "API", a cached extraction exists, and the user clicks Re-read
- **THEN** a confirmation dialog SHALL appear with text "Re-reading on the API backend will incur a billable call. Continue?" and the request SHALL only be sent if the user confirms

### Requirement: Draft pool textarea is read-source only
The textarea SHALL be user-editable (so a transcriber can clean up the AI draft) but its content SHALL NOT auto-fill any structured field (collector, taxon, locality, identification, etc.) in this change. A label "AI draft — verify before using" SHALL be visible above the textarea.

#### Scenario: Editing draft does not modify form
- **WHEN** a transcriber edits the textarea
- **THEN** no structured field input in the right form panel SHALL change
- **AND** the form's existing dirty-state and save-button behaviour SHALL be unaffected

#### Scenario: Draft persists across modal navigation
- **WHEN** a transcriber navigates Prev/Next in the modal and returns to the original specimen
- **THEN** the textarea SHALL re-hydrate from the persisted `unit_ai_extraction` (no fresh API call)

### Requirement: Per-session attempt history
The panel SHALL render a compact list of attempts made *during the current modal session* (cleared on modal close). Each entry SHALL show backend, model, latency in ms, cached flag, and a timestamp.

#### Scenario: Multiple attempts compared
- **WHEN** a transcriber clicks Re-read three times across both backends
- **THEN** the history list SHALL show three entries in reverse chronological order with the textarea showing the most recent reply

#### Scenario: History cleared on close
- **WHEN** the transcriber closes the modal and re-opens it for the same specimen
- **THEN** the in-session history SHALL be empty (the textarea still hydrates from the persisted row, but historical attempts are not surfaced)

### Requirement: Translations
All AI panel strings SHALL be added to `app/static/js/annotate/i18n.js` with Traditional Chinese translations. Minimum strings: panel title, backend labels, action buttons, status messages, confirmation copy.

#### Scenario: Panel renders in zh
- **WHEN** the page loads with `g.lang_code == "zh"`
- **THEN** every visible string in the AI panel SHALL render in Traditional Chinese
