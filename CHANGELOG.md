# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.3] — 2026-06-10

### Added

- `safe_inline` template filter — renders an allow-listed subset of
  inline HTML (`<strong>`, `<em>`, `<b>`, `<i>`, `<u>`, `<br>`, `<p>`,
  `<sub>`, `<sup>`) carried over from the Drupal import; attributes
  are stripped so XSS isn't possible.
- PDF download on the Export modal for Books / Persons / Places via
  WeasyPrint. Routes: `/<entity>/<slug>/export.pdf`.
- Wagtail snippet admin gains a real `SnippetViewSet` per model with
  `search_fields`, `list_filter` and `list_display` — 9 entity-flavour
  ViewSets (Book / Person / City / BookAuthor / Edition / Translation
  / Mention / Preface / Production), 4 catalog dimensions
  (Publisher / Series / Topic / Occupation), 14 lookup tables.
- Contact form (`/contact/`) rendered through `django-crispy-forms`
  + Bootstrap 5; hCaptcha challenge keyed on `HCAPTCHA_SITE_KEY` /
  `HCAPTCHA_SECRET_KEY` (both empty disables the widget); footer
  link under About.
- `Topic.slug` + `Occupation.slug` columns + migration; Hebrew
  taxonomy entries can now be linked.
- `home.management.commands.audit_data_quality`,
  `clean_person_names`, `mark_orphan_places_draft` data audit + fix
  commands.
- `home/migrations/0030_clean_person_names.py` data migration
  promotes the one-shot name cleaner to a permanent fix.
- `home/migrations/0031_strip_php_empty_arrays.py` empties the
  Drupal-6 `a:0:{}` empty-array remnants out of every Book TextField.

### Changed

- Header actions (Cite / Export / Permalink, VIAF / GND chips on
  Person) move from outline buttons to `.badge.text-bg-secondary`;
  "View digital copy" stays the only solid button.
- Detail-section dl-row pairs use CSS Grid instead of Bootstrap flex
  — long Hebrew dd cells no longer wrap to the next row.
- Hebrew / mixed-direction content in section `<dd>` and `<li>`
  elements auto-aligns via `dir="auto"` + `unicode-bidi: plaintext`.
- Main menu becomes a sticky hamburger + offcanvas on mobile;
  desktop nav scrolls with the page.
- Catalog detail link in `/places/`, `/topics/`, `/occupations/` uses
  the persisted `.slug` instead of recomputing `name|slugify`.
- Library catalog ID URLs refreshed for Bar Ilan, British Library,
  HUJI, New York (CLIO), with Frankfurt URNs routing through the
  NBN resolver. Stray `<a>`-style HTML noise is stripped before the
  URL is built or the cell rendered.
- Wrapper max-width tuned to 1080 px after a brief excursion to
  1480 px; `dl.row dt` color inherits body grey.
- Person-name leading-hyphen fix: `(Feder)-Guttmann` now cleans to
  `Guttmann` (PR #76).
- Contact form mail delivery: settings fall back to safe defaults,
  EMAIL_BACKEND switches to MailHog in dev, `CONTACT_TO_EMAIL` is
  used when the Wagtail page leaves the recipient field empty.

### Fixed

- `0.0` legacy noise in detail-page section rendering — already
  handled by the `clean_value` filter; reaffirmed via the
  `safe_inline` chain.
- CSRF cookie no longer cached out of the GET `/contact/` response
  (`@never_cache` on `ContactPage.serve()`).
- HTML5 form-validation re-enabled on the contact form (`novalidate`
  removed).
- Topbar sticky behaviour scoped to mobile via media query (PR #100).

### Dependencies

- `weasyprint==69.0` pinned for PDF rendering; `libpango-1.0-0`,
  `libpangoft2-1.0-0`, `libharfbuzz0b`, `libfontconfig1`,
  `fonts-dejavu` added to the Docker apt block.

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

[Unreleased]: https://github.com/judaicalink/haskala/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/judaicalink/haskala/releases/tag/v1.0.3
[1.0.2]: https://github.com/judaicalink/haskala/releases/tag/v1.0.2
[1.0.1]: https://github.com/judaicalink/haskala/releases/tag/v1.0.1
[1.0.0]: https://github.com/judaicalink/haskala/releases/tag/v1.0.0
