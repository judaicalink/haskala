# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] — 2026-06-09

### Security

- Bind dev ports for Solr (`8983`), Fuseki (`3030`) and MailHog
  (`1025` / `8025`) to `127.0.0.1` so they aren't reachable from
  any host on the LAN during local development.
- New CI step runs `pip-audit --strict` and `npm audit
  --audit-level=high` on every push so known CVEs in
  `requirements.txt` / `package-lock.json` block the build.

### Added

- `CHANGELOG.md` (this file).
- `.github/dependabot.yml` opens weekly update PRs for pip / npm /
  github-actions against the `development` branch.
- `data/{backups/daily,backups/monthly,initial,awstats/logs}/.gitkeep`
  pin the expected bind-mount sub-tree so first-time
  `docker compose up` finds the paths and contributors see the
  layout without booting the stack.

### Removed

- `SPARQLWrapper` dependency. The only call site
  (`home.models.get_people_names`) was unreachable dead code with a
  hardcoded `localhost` Fuseki URL; SPARQL writes flow through
  `djangordf.backends.fuseki.FusekiBackend` now (see v1.0.1).

## [1.0.1] — 2026-06-09

### Changed

- `haskala_rdf.push` now routes the SPARQL Update path through
  `djangordf.backends.fuseki.FusekiBackend.update()`. The Graph
  Store Protocol (PUT) path stays on raw `requests` because
  `djangordf` does not cover GSP.
- Settings auto-select `djangordf` `FusekiBackend` when
  `HASKALA_SPARQL_PUSH_URL` is set, falling back to the bundled
  `InMemoryBackend` otherwise.

### Dependencies

- `djangordf>=0.4.1` (0.4.0's wheel was missing the `backends/`
  subpackage; fixed upstream).

## [1.0.0] — 2026-06-08

First release after the full roadmap-plus-hardening sweep.

### Added

- Django/Wagtail library catalog with `Book` / `Person` / `City` as
  snippets, all three with `RevisionMixin` + `DraftStateMixin`.
- Inline `BookAuthor` editing on the `Book` form via `ParentalKey` +
  `ClusterableModel`.
- Slug pipeline strips non-Latin scripts before transliteration;
  Hebrew-only entries fall back to `<model>-<8-uuid>`.
- Public detail / list views, sitemap and RDF export filter
  `live=True` so drafts disappear from the public site.
- RDF export pipeline (`manage.py export_rdf`) produces gzipped
  Turtle data + meta graph, BEACON file and Markdown frontmatter.
- Optional auto-push to a SPARQL endpoint (HTTP Graph Store Protocol
  or SPARQL 1.1 Update) via `HASKALA_SPARQL_PUSH_URL`.
- Persistent host-bound layout under `HASKALA_DATA_DIR` (default
  `./data`) for postgres dumps, fuseki TDB2, awstats output and the
  postfix spool.
- Postgres restore-on-init: scans `data/backups/{daily,monthly}/`,
  falls back to `data/initial/haskala.sql`, otherwise leaves the
  database empty.
- `backups` service runs daily `pg_dump` with 14-day retention plus
  a monthly snapshot kept for 12 months.
- Production overlay (`docker-compose.prod.yml`) layers `monit`
  watchdog with docker-socket restarts, `awstats` web statistics,
  `cron` container for monthly fuseki dumps + AWStats + logrotate,
  and a `postfix` sidecar that relays through the institutional SMTP
  server.
- nginx fronts the whole stack; production locations `/awstats/` +
  `/monit/` proxy via runtime DNS resolution so dev still starts
  cleanly without those upstreams.
- HTTPS hardening in `settings/production.py`:
  `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, HSTS (1 year,
  `includeSubDomains`, preload), `SECURE_REFERRER_POLICY`,
  `X_FRAME_OPTIONS=DENY`.
- CI exercises the backup + restore round-trip plus the monthly
  rollover on every push.

[Unreleased]: https://github.com/judaicalink/haskala/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/judaicalink/haskala/releases/tag/v1.0.2
[1.0.1]: https://github.com/judaicalink/haskala/releases/tag/v1.0.1
[1.0.0]: https://github.com/judaicalink/haskala/releases/tag/v1.0.0
