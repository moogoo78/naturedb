## Decision: gate by `Host:` header in the frontpage URL preprocessor, not by a separate Flask app or by Traefik path rewrite

**Choice**: Reuse the single `flask_app` and the existing `frontpage` blueprint. Recognize scribe hosts inside `pull_lang_code` (the blueprint's `url_value_preprocessor`) and gate which endpoints are allowed on those hosts. The `frontpage.index` handler — already the `/` endpoint — branches on `g.site == '__SCRIBE__'` and renders `annotate/index.html` directly.

**Why**:
- The dispatch site for "what does this host serve at `/`" already exists in `pull_lang_code`. It already handles the portal host (`g.site = '__PORTAL__'`) and per-collection sites (`g.site = <Site>`). Adding a third sentinel (`'__SCRIBE__'`) keeps the host-routing decisions in one place rather than splitting them across Traefik labels and Python.
- Same Flask app means `/static/*`, `/api/*`, error pages, JWT cookies, and Babel locale negotiation all behave identically on scribe and on the portal — no duplicate config, no separate WSGI worker, no second container.
- Works locally without Traefik. Local dev resolves `scribe.sh21.ml` via `/etc/hosts` and hits Flask directly on `:5000`; the same code paths fire in prod behind Traefik.

**Alternatives considered**:
- *Traefik path rewrite at the edge* (router on `Host(scribe.…) && Path("/")` with a `replacepathregex` middleware to `/annotate`). Rejected: requires keeping a `/annotate` route in Flask just so Traefik has a target, which contradicts the goal of removing that URL from every host. Also doesn't help local dev, where Traefik isn't in the picture.
- *Second Flask app / blueprint mounted at `/`*: would need its own URL value preprocessor, its own Babel setup, and would still have to coexist with the existing `frontpage.index` rule. Higher complexity for no behavior win.
- *Flask `host_matching=True`*: applies to every route in the app and forces every existing rule to declare a host pattern. Too invasive for a single subdomain.

## Decision: register the scribe gate as the *first* branch in `pull_lang_code`, before the portal-host check

**Choice**: The host-comparison block ordering inside the preprocessor is `SCRIBE_HOSTS → PORTAL_HOST → Site.find_by_host → abort(404)`.

**Why**: Putting the scribe check first lets it short-circuit before the portal-host branch's path-restriction logic runs (which would otherwise 404 a non-`/` request on a scribe host with a *less* specific message and skip our host-aware gating). It also means a scribe host that accidentally also matches a row in the `Site` table (it shouldn't, but defensively) still routes to the explorer rather than to a per-collection site template.

## Decision: `g.site = '__SCRIBE__'` sentinel, not `None` or a fake `Site` instance

**Choice**: Set `g.site` to the string literal `'__SCRIBE__'` and have `frontpage.index` branch with `if g.site == '__SCRIBE__'` before the `'__PORTAL__'` and per-site cases.

**Why**:
- Symmetric with the existing `'__PORTAL__'` sentinel, so the pattern is recognizable and the type of `g.site` stays consistently "string literal sentinel OR Site ORM instance".
- Lets us 404 *all* other endpoints on scribe hosts at the preprocessor layer — handlers downstream don't have to defensively check `g.site` because they're never reached.
- A real `Site` row would imply we want collection-aware behavior (header, footer, taxon map), which we explicitly don't.

## Decision: hard-coded `SCRIBE_HOSTS` tuple in `Config`, not env-var driven

**Choice**: `Config.SCRIBE_HOSTS = ('scribe.naturedb.org', 'scribe.sh21.ml')` — a literal tuple, not `os.getenv(...)`.

**Why**: The set of scribe hosts is small, known, and tied to deployment topology that we control. Env-driven config (à la `PORTAL_HOST`) makes sense when the value differs per-deployment of a single product (one portal hostname per environment); for scribe we want both prod and dev to be recognized in any environment, so a literal is simpler and has no surprise from missing env wiring. If we ever need per-deploy values we can promote to env then.

## Risks / Trade-offs

- **External `/annotate` bookmarks 404**. Acceptable: v1 was unlinked from `base.html` nav and called out as "public-but-unlinked" in the original proposal, so the bookmark surface is small.
- **Single Flask app means a misconfigured scribe host could reach admin or API routes**. Mitigated by the explicit `endpoint == 'frontpage.index'` allowlist in the preprocessor — every other blueprint endpoint hits `abort(404)` on a scribe host. Admin and API blueprints have their own preprocessors / decorators that would also reject anonymous access, so this is defence-in-depth rather than the primary gate.
- **DNS/cert dependency for prod**: `scribe.naturedb.org` must live on the same Cloudflare zone the DNS-01 resolver is configured for (`CF_DNS_API_TOKEN`). If we ever introduce a scribe host outside that zone, the cert resolver config has to grow.

## Open questions

1. *Should the scribe host serve `/static/*` via the same Flask static handler, or should we move static under a `cdn.scribe.…` host eventually?* Current default: same handler. Defer until the static asset bundle grows large enough to justify a CDN.
2. *Should auth eventually be scoped per-host (login on scribe issues a different cookie than login on the portal)?* Current default: shared session cookie scoped to `.naturedb.org`. Revisit when scribe gets real auth.
