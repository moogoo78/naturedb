## MODIFIED Requirements

### Requirement: Annotation explorer route
The application SHALL expose the Explorer view as the default screen at the root path (`/`) of any host listed in `Config.SCRIBE_HOSTS` (production: `scribe.naturedb.org`; local development: `scribe.sh21.ml`). The route SHALL be served by the existing `frontpage` blueprint via its `frontpage.index` endpoint and SHALL NOT require authentication in v1. The Explorer SHALL NOT be reachable under any other path on a scribe host, and SHALL NOT be reachable on the portal host or on per-collection site hosts.

#### Scenario: Anonymous visitor opens the explorer on a scribe host
- **WHEN** an unauthenticated visitor requests `GET /` with `Host: scribe.naturedb.org` (or `scribe.sh21.ml` in dev)
- **THEN** the server SHALL return HTTP 200 with the Explorer view rendered (`annotate/index.html`)

#### Scenario: Direct link to a specimen
- **WHEN** a visitor opens `/#<catalog>` on a scribe host where `<catalog>` matches a specimen's `id` in the mock dataset
- **THEN** the page SHALL load with the Annotation view active for that specimen
- **AND** the back/forward browser buttons SHALL toggle between Explorer and Annotation views without a server round-trip

#### Scenario: Unknown specimen in hash
- **WHEN** a visitor opens `/#<catalog>` on a scribe host for a catalog not present in the mock dataset
- **THEN** the page SHALL fall back to the Explorer view and the hash SHALL be cleared

#### Scenario: Explorer is not reachable on the portal host
- **WHEN** a visitor requests `GET /annotate` (or `GET /<lang_code>/annotate`) with `Host: <PORTAL_HOST>`
- **THEN** the server SHALL return HTTP 404

#### Scenario: Explorer is not reachable on a per-collection site host
- **WHEN** a visitor requests `GET /annotate` (or `GET /<lang_code>/annotate`) with a `Host:` matching any row in the `Site` table
- **THEN** the server SHALL return HTTP 404

#### Scenario: Non-root paths on a scribe host are 404
- **WHEN** a visitor requests any path other than `/` (e.g. `GET /annotate`, `GET /about`, `GET /specimens/...`) with `Host: scribe.naturedb.org`
- **THEN** the server SHALL return HTTP 404

### Requirement: Mock specimen dataset
The page SHALL render against a static JSON dataset shipped at `app/static/js/annotate/specimens.mock.json` containing the 12 specimens and 4-key facet structure ported from `nature-scribe/project/data.jsx`. The page SHALL NOT issue any database queries or authenticated API calls in v1.

#### Scenario: Dataset shape
- **WHEN** the JS module loads `specimens.mock.json`
- **THEN** the response SHALL be a JSON object with two top-level keys, `specimens` (array) and `facets` (object with `kingdom`, `family`, `region`, `status` keys)
- **AND** each specimen SHALL include the fields `id`, `catalog`, `kingdom`, `taxon`, `common`, `family`, `collector`, `collected`, `locality`, `completeness`, `annotations`, `pending`, `status`, `medium`, `color`

#### Scenario: No DB access
- **WHEN** the request `GET /` on a scribe host is served
- **THEN** the request handler SHALL NOT call `session.execute`, `session.query`, or any model class

## ADDED Requirements

### Requirement: Scribe host configuration
The application SHALL expose the set of recognized scribe subdomains via `Config.SCRIBE_HOSTS`, a tuple of bare hostnames (no scheme, no port). The set SHALL include the production subdomain `scribe.naturedb.org` and the local-development subdomain `scribe.sh21.ml`.

#### Scenario: Config tuple shape
- **WHEN** application code reads `current_app.config['SCRIBE_HOSTS']`
- **THEN** the value SHALL be a tuple of strings, each being a bare hostname (no protocol, no port, no path)

#### Scenario: Host comparison strips port
- **WHEN** the frontpage preprocessor compares `request.headers['Host']` against `SCRIBE_HOSTS`
- **THEN** the comparison SHALL strip a trailing `:<port>` from the header value before membership testing, so that `scribe.sh21.ml:5000` matches the bare `scribe.sh21.ml` entry in the tuple

### Requirement: `__SCRIBE__` site sentinel
When a request arrives on a scribe host and is allowed through the preprocessor, `g.site` SHALL be set to the string literal `'__SCRIBE__'`. The `frontpage.index` handler SHALL branch on this sentinel and render `annotate/index.html` directly, before the `'__PORTAL__'` and per-site branches.

#### Scenario: Sentinel value is set
- **WHEN** `pull_lang_code` accepts a request on a scribe host for the `frontpage.index` endpoint
- **THEN** `g.site` SHALL equal the string `'__SCRIBE__'` when the handler runs

#### Scenario: Index handler renders annotate template under the sentinel
- **WHEN** `frontpage.index` runs with `g.site == '__SCRIBE__'`
- **THEN** the response SHALL be `render_template('annotate/index.html')`
- **AND** the handler SHALL NOT touch `Site`, `Article`, `Unit`, or `get_site_stats`
