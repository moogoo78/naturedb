# Development

## From a fresh clone

```bash
cp dotenv.sample .env
docker compose up -d --build
docker compose exec flask flask initdata
```

`docker compose up` also brings up adminer on `:8080` (that comes from
`compose.override.yml`, which compose picks up automatically next to
`compose.yml`). `/srv/start` runs `flask migrate` before serving, and flask now
waits on the postgres healthcheck, so the schema exists by the time compose
returns. `initdb/00-extensions.sql` creates PostGIS on the very first boot —
without it the `675f3d3e99af` migration (`named_area.geom_mpoly`) fails.

`flask initdata` seeds the example `demo` site: site / organization /
collection, area classes, gazetteer, taxa, people, assertion types, 8 specimen
records and an `admin` / `admin` account. The data lives in `app/initdata.py`
and the command is idempotent. See the README for what it contains and how to
adapt it.

Notes on the volume layout: the compose files bind-mount `../naturedb-volumes/`
(pgdata, bucket, uploads, logs) — a sibling of the repo, so it survives
`docker compose down -v`. Docker creates the directories on first run.

## From a production dump instead

1. Set `.env` (`WEB_ENV=dev`; `ACME_EMAIL` must be valid or Let's Encrypt will
   error in prod).
2. `make db-dump`, or copy a gzipped dump into `initdb/` by hand. The postgres
   entrypoint runs everything in that directory in filename order on an empty
   `PGDATA`, so `00-extensions.sql` lands before the dump.
3. `docker compose up -d --build`
4. Point the site at your hostname:
   `UPDATE site SET host = '{my-domain}' WHERE id = {my-id};`
5. Copy the site settings to `app/settings/{site.name}.json` (that whole
   directory is gitignored apart from `demo.json`).

For a prod/staging host, also copy `compose.prod-vhosts-sample.yml` to
`compose.prod-vhosts.yml` and put the per-domain Traefik router labels in it.

## Github Action

`ssh-gen`

create `id_rsa-github` and `id_rsa.github.pub`

in server:

```sh
cat id_rsa.github.pub >> ~/.ssh/authorized
```

In Github repo setting page:

copy id_rsa-github (private) to github settings page, set secrets `$KEY`
