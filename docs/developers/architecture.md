# Architecture overview

The Haskala platform is a Django + Wagtail application backed by
Postgres and ringed by service containers for caching, search, RDF
storage and dev mail.

## Containers

```
                 +-----------+
   browser  -->  |   nginx   |  (host port 8080)
                 +-----------+
                       |
                       v
                 +-----------+      +----------+
                 |    web    |  --> |    db    |  (Postgres 16, /docker-entrypoint-initdb.d/haskala.sql)
                 |  gunicorn |      +----------+
                 |  django 6 |
                 |  wagtail  |  --> +----------+
                 |   7.4     |      |   redis  |  (django-redis cache)
                 +-----------+      +----------+
                       |
                       +---->  solr        (search index)
                       +---->  fuseki      (Apache Jena triple store)
                       +---->  mailserver  (MailHog, dev SMTP + UI)
```

`web` is the only container the browser ever talks to; everything else
is reached via service names on the docker network.

## Django apps

- `home` — the catalogue: every public model
  (Book, Person, City, Publisher, Series, Topic, Occupation, …),
  the public views, the search view, the importers, the management
  commands.
- `haskala` — the Django project itself: `settings/`, `urls.py`,
  `wsgi.py`. The `dev` and `production` settings modules both inherit
  from `base.py`.
- `search` — the search index integration with Solr.
- `haskala_rdf` — the RDF export and ontology generator (not a Django
  app — a plain Python package used by management commands).

## Frontend pipeline

Two source trees feed two static bundles:

- `haskala/static/scss/*.scss` → `haskala/static/css/haskala.css`
  via `npm run build:css` (`sass`).
- `haskala/static/js/app-entry.js` → `haskala/static/js/app.js`
  via `npm run build:js` (`esbuild`). The detail-page interactions
  live in `book_detail.js` and are loaded as an ES module per page.

The built bundles are git-ignored; `collectstatic` writes them into
the named volume `static_data` that nginx serves from
`/var/www/static/`.

## Detail page rendering

The Book, Person and Place detail pages share a structure:

1. A small Python module under `home/` (`book_detail.py`,
   `person_detail.py`, `place_detail.py`) defines an ordered
   `SECTIONS` list and a `visible_sections()` function that returns
   only the sections with data for the given record.
2. The view passes `visible_sections` into the context together with
   the record.
3. The page template iterates `visible_sections` twice — once for the
   sticky TOC, once for the content — and includes a per-section
   partial at `_sections/<slug>.html` for each visible entry.

This pattern keeps "which sections exist" and "what each section
looks like" cleanly separated, and is what new detail pages should
follow.

## Caching

The `book_detail_view`, `person_detail_view` and `place_detail_view`
are wrapped in `@cache_page(60 * 60)`; cache invalidation is
manual (`FLUSHALL`) for now. In dev the cache should be flushed
between major template changes so editors and developers see the
new render right away.

## Edge layer (nginx)

The `nginx` container sits between the browser and gunicorn:

- **gzip + gzip_static**: text-like responses (HTML, CSS, JS, JSON,
  SVG, fonts) are gzip-compressed on the fly. `gzip_static on` lets
  nginx prefer a pre-built `<file>.gz` sibling when one exists so we
  can ship pre-compressed bundles from `collectstatic` later without
  reconfiguring. Compression cuts the home HTML from ~50 KB to ~6 KB
  and `haskala.css` from ~250 KB to ~36 KB.
- **Static asset caching**: `/static/` carries
  `Cache-Control: public, max-age=2592000, immutable` (30 days).
  The asset bundles do not yet carry a content hash in their
  filename — once `ManifestStaticFilesStorage` is turned back on,
  this can safely go to 1 year.
- **Upstream keepalive**: `upstream haskala_web` keeps up to 16 idle
  TCP connections to gunicorn open, so each request does not pay
  the connect-handshake cost. The reverse-proxy block sets HTTP/1.1
  and an empty `Connection:` header on the upstream side.
- **JS deferred**: the global `app.js` script tag in `base.html`
  carries `defer` so it does not block the first render.
