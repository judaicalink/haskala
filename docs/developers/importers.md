# Importer workflow

The `home/management/commands/import_*` family loads the catalogue
from CSV exports of the previous Drupal 6 system.

## When importers run

- **On a fresh database** — to seed the catalogue from scratch.
- **After a corrective export pass** — when editorial team produces a
  new round of CSV corrections.

Day-to-day admin edits go through the Wagtail UI, not the importers.

## Source CSVs

The CSVs live under `research/export/` (repo-relative). They are not
committed; copy the latest set in before a run.

Each importer expects a fixed filename. Inspect the source of the
command you want to run (or its `--help`) to learn which.

## Recommended order on a fresh database

1. **Vocabularies first** — taxonomies, the alignment vocabulary, the
   textual / footnote vocabularies, cities and geolocations:

   ```bash
   docker compose exec web python manage.py import_haskala_taxonomies
   docker compose exec web python manage.py import_haskala_alignment
   docker compose exec web python manage.py import_haskala_textual_vocabs
   docker compose exec web python manage.py import_haskala_footnote_locations
   docker compose exec web python manage.py import_cities
   ```

2. **Entities second** — persons and books:

   ```bash
   docker compose exec web python manage.py import_haskala_persons
   docker compose exec web python manage.py import_haskala_books
   ```

3. **Relations last** — BookAuthor rows, Mentions, Prefaces,
   Productions:

   ```bash
   docker compose exec web python manage.py import_haskala_relations
   ```

The combined `import_haskala_entities` command runs the entity layer
in one sweep; pick it instead of `_persons` + `_books` when convenient.

## Idempotency

All importers match rows by `legacy_nid` (entities) or `legacy_tid`
(taxonomies). Re-running an importer updates the existing row rather
than creating a duplicate. This means an editorial correction in the
CSV can be replayed safely.

Exception: `import_haskala_relations` previously had a known issue
where re-running clobbered multi-valued M2Ms. That is fixed (see
commit `4977c1d`), but verify with a small test run before pointing
it at the live database.

## Backup before any bulk run

```bash
docker compose exec db pg_dump -U haskala haskala \
    > backups/$(date +%Y-%m-%d)-pre-import.sql
```

Restore:

```bash
docker compose exec -T db psql -U haskala -d haskala < backups/<file>.sql
```

## After a run

- Re-index Solr: `python manage.py update_index`.
- The next cron run of `export_rdf` will pick up the new data; force
  a run with
  `docker compose exec web python manage.py export_rdf`.
- Flush the cache so the public site reflects the new state:
  `docker compose exec redis redis-cli FLUSHALL`.

## Adding a new importer

The existing commands follow a shared shape: open the CSV with
`csv.DictReader`, look up an existing row by `legacy_nid`, then
`get_or_create` / `update`. Keep the new command in that pattern so
re-runs stay idempotent and so a future maintainer can predict its
behaviour without reading the source.
