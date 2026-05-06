## 1. Configuration

- [x] 1.1 Add `SCRIBE_HOSTS = ('scribe.naturedb.org', 'scribe.sh21.ml')` to `Config` in `app/config.py`.

## 2. Host gating in the frontpage preprocessor

- [x] 2.1 In `app/blueprints/frontpage.py::pull_lang_code`, add a branch before the `PORTAL_HOST` check: if `request.headers['Host']` (port-stripped via `.split(':')[0]`) is in `current_app.config['SCRIBE_HOSTS']`, allow only `endpoint == 'frontpage.index'` (set `g.site = '__SCRIBE__'`, return `True`); otherwise `abort(404)`.
- [x] 2.2 In `frontpage.index`, branch on `g.site == '__SCRIBE__'` *before* the `'__PORTAL__'` and per-site branches; return `render_template('annotate/index.html')`.

## 3. Remove the old `/annotate` route

- [x] 3.1 Delete the `@frontpage.route('/annotate', defaults={'lang_code': DEFAULT_LANG_CODE})` and `@frontpage.route('/<lang_code>/annotate')` decorators and the `annotate(lang_code)` handler from `app/blueprints/frontpage.py`.
- [x] 3.2 Verify no in-tree caller uses `url_for('frontpage.annotate')` (grep). If found, replace with the new host-rooted URL.

## 4. Local-dev verification

- [x] 4.1 Add `scribe.sh21.ml` to `/etc/hosts` pointing at the dev box (operator step, not a code change).
- [x] 4.2 `curl -sI -H "Host: scribe.sh21.ml" http://localhost:5000/` returns `200`.
- [x] 4.3 `curl -sI -H "Host: scribe.sh21.ml" http://localhost:5000/annotate` returns `404`.
- [x] 4.4 `curl -sI -H "Host: <PORTAL_HOST>" http://localhost:5000/annotate` returns `404`.
- [x] 4.5 `curl -sI -H "Host: <PORTAL_HOST>" http://localhost:5000/` still returns `200` (portal landing).

## 5. Production deployment

- [ ] 5.1 In the real prod-vhosts override file (the live counterpart of `compose.prod-vhosts-sample.yml`), add a Traefik router for `Host(scribe.naturedb.org)` on the `flask` service: rule, `entrypoints=websecure`, `tls.certresolver=myresolver`. No middleware, no path rewrite.
- [ ] 5.2 Confirm `scribe.naturedb.org` DNS exists on the Cloudflare zone configured for the DNS-01 resolver and resolves to the prod box.
- [ ] 5.3 Roll out and verify cert issuance for the new SAN succeeds in Traefik logs on first request.
- [ ] 5.4 Smoke test: `curl -sI https://scribe.naturedb.org/` returns `200`; `curl -sI https://scribe.naturedb.org/annotate` returns `404`; `curl -sI https://${PORTAL_HOST}/annotate` returns `404`.
