# Local setup

The canonical dev environment is the Docker Compose stack. A bare-metal
fallback is documented below for when you can't run Docker.

## Docker

```bash
git clone git@github.com:judaicalink/haskala.git
cd haskala
docker compose up -d
```

On first boot the `db` container runs
`docker/db-init/00-restore-or-seed.sh` against the (empty) postgres
data volume. The script:

1. looks for the newest dump in `${HASKALA_DATA_DIR}/backups/daily/`,
   then `monthly/`, and restores it via `psql`;
2. if no backup exists, falls back to
   `${HASKALA_DATA_DIR}/initial/haskala.sql`;
3. if neither exists, leaves the database empty for `manage.py
   migrate` to populate.

`HASKALA_DATA_DIR` defaults to `./data`; set it via `.env` to point at
a production location like `/srv/haskala`. After the DB is ready the
`web` container runs `python manage.py migrate`, nginx proxies
<http://localhost:8080/> to gunicorn, and Solr, Redis, Fuseki (persistent
TDB2 at `${HASKALA_DATA_DIR}/fuseki/`) and MailHog come up alongside.

The `backups` service runs a daily `pg_dump` at 02:30 UTC into
`${HASKALA_DATA_DIR}/backups/daily/` (kept 14 days). On the first day of
the month it additionally drops a monthly snapshot under
`${HASKALA_DATA_DIR}/backups/monthly/` (kept 365 days). Force a backup
at any time with:

```bash
docker compose exec backups /usr/local/bin/backup.sh
```

Restore the latest dump (across daily + monthly) into the running DB
with:

```bash
docker compose exec backups /usr/local/bin/restore.sh latest
```

A superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

The Wagtail admin is then at <http://localhost:8080/admin/>.

### Tail the logs

```bash
docker compose logs -f web
```

### Restart after a model change

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose restart web
```

Gunicorn does not auto-reload code changes; restart `web` after
edits.

### Frontend assets

The CSS bundle (`haskala/static/css/haskala.css`) and the JS bundle
(`haskala/static/js/app.js`) are generated from sources by npm:

```bash
npm install
npm run build:css   # sass haskala.scss -> haskala.css
npm run build:js    # esbuild app-entry.js -> app.js
npm run copy:icons  # Bootstrap-Icons font + json
```

The generated files are git-ignored. Rebuild them after editing the
SCSS or JS sources and restart the web container so the static
collector picks up the new bundle.

### Tests + flake8

```bash
docker compose exec web python manage.py test
flake8 --max-line-length=120 home/ haskala/
```

Both must pass on every commit. flake8 runs on the host venv;
`pip install -r requirements.txt` in a local venv suffices to get a
copy.

## Bare-metal

If Docker isn't available:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You'll need a local Postgres 16 (or compatible) and Redis available
to the app. Set the connection strings via environment variables
(`DATABASE_URL`, `REDIS_URL`) or in `haskala/settings/local.py`. Then:

```bash
psql -d haskala -f haskala.sql        # seed
python manage.py migrate
python manage.py runserver
```

Solr and Fuseki are optional for most dev workflows; the views that
need them degrade gracefully when they're absent.

## Common gotchas

- **CSRF "Origin checking failed"** on login through the nginx proxy
  → ensure `CSRF_TRUSTED_ORIGINS` includes the scheme and host the
  browser is on. `dev.py` does this for `http://localhost:8080`.
- **`Apps aren't loaded yet`** when scripting through `manage.py
  shell -c` → pass `-e DJANGO_SETTINGS_MODULE=haskala.settings.dev`
  to `docker compose exec`.
- **Stale page after a code change** → flush the Redis cache with
  `docker compose exec redis redis-cli FLUSHALL`, then restart `web`.
