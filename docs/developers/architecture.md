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
