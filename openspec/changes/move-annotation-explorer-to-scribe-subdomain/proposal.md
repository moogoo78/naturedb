## Why

The Nature-Scribe explorer shipped in `add-annotation-explorer` lives at `/annotate` on every host (portal and per-collection sites). That couples a forward-looking annotation product to URL space owned by the existing collection sites and makes it impossible to evolve auth, branding, or eventual API surface for Scribe independently. We want Scribe to live behind its own subdomain so it can grow into a standalone surface without leaking routes onto sites whose users don't care about it.

## What Changes

- Add `Config.SCRIBE_HOSTS = ('scribe.naturedb.org', 'scribe.sh21.ml')` listing the production subdomain and the local-dev subdomain.
- Move host gating into `frontpage.pull_lang_code`: a request whose `Host:` (port stripped) is in `SCRIBE_HOSTS` is allowed only for the `frontpage.index` endpoint; every other path on a scribe host returns 404. The site sentinel becomes `g.site = '__SCRIBE__'`.
- `frontpage.index` branches on the sentinel and renders `annotate/index.html` directly when the host is a scribe host.
- **BREAKING (intentional)**: Remove the `/annotate` route definition (and its `/<lang_code>/annotate` variant) from the frontpage blueprint. `GET /annotate` returns 404 on the portal host and on every per-collection site host.
- Production deploys gain a Traefik router for `Host(scribe.naturedb.org)` that points at the same Flask service (no path rewrite needed since Scribe is served at `/`). Local dev resolves `scribe.sh21.ml` via `/etc/hosts` to the dev box.

## Capabilities

### Modified Capabilities
- `annotation-explorer`: URL/hosting requirements change — the explorer is reached via the root of a recognized scribe subdomain instead of a `/annotate` path on every host.

## Impact

- **Code**: `app/config.py` (new constant), `app/blueprints/frontpage.py` (preprocessor branch + index sentinel branch, deleted `annotate` route handler).
- **Deployment**: production prod-vhosts override file gains a Traefik router for `scribe.naturedb.org`; DNS for the new subdomain must resolve and, in prod, must live on the Cloudflare zone used by the existing DNS-01 cert resolver.
- **Templates**: `app/templates/annotate/index.html` is unchanged and still depends only on `g.lang_code` (set by the preprocessor before the sentinel branch fires).
- **Existing links**: nothing in the repo or admin UI links to `/annotate`, so the route removal does not break any in-tree caller. External bookmarks to `/annotate` will 404 — acceptable since v1 was unlinked from `base.html` nav.
