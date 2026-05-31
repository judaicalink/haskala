# Data imports

This page is for editors who need to load or reload data in bulk.
For one-off corrections, use the [Wagtail admin](wagtail-admin.md)
instead.

## When to use the importers

The current dataset was imported from the previous Drupal 6 system in
2023-2024 and corrected in subsequent rounds. The importers stay in
the codebase because:

- A future export pass from the old system may need re-running.
- The same code is the canonical source for which Drupal column maps
  to which Django field.
- New CSV exports of supporting vocabularies still arrive from time
  to time.

Don't run an importer to "fix" a single record — that's an admin-UI
task.

## CSV expectations

All importers read CSV files from the `research/export/` directory
(repo-relative). Each command's `--help` flag lists the exact CSV it
expects. The CSVs are not committed; they live with the editorial
team and are copied in before a run.

```bash
docker compose exec web python manage.py import_haskala_books --help
```

## Available commands

| Command                                  | Loads                                                       |
| ---------------------------------------- | ----------------------------------------------------------- |
| `import_cities`                          | Cities and their geolocations                               |
| `import_haskala_taxonomies`              | Topic, Occupation, Gender, Series, Publisher etc.           |
| `import_haskala_alignment`               | The Alignment vocabulary                                    |
| `import_haskala_textual_vocabs`          | OriginalType and TextualModel vocabularies                  |
| `import_haskala_footnote_locations`      | FootnoteLocation entries                                    |
| `import_haskala_persons`                 | Person records                                              |
| `import_haskala_books`                   | Book records                                                |
| `import_haskala_entities`                | Persons, books and supporting models in one sweep           |
| `import_haskala_relations`               | BookAuthor / Mention / Preface / Production join rows       |

The recommended order on a fresh database is taxonomies first, then
entities, then relations. The `import_haskala_*` family is idempotent
when re-run — rows are matched by `legacy_nid` / `legacy_tid` and
updated rather than duplicated.

## Re-running on the live database

Always take a Postgres backup before a bulk import. The dedicated
`backups` container handles this in one command (it writes a
timestamped, gzipped dump into the `backups_data` volume):

```bash
docker compose run --rm backups backup.sh
```

If something goes wrong, restore the most recent dump:

```bash
docker compose run --rm backups restore.sh latest
docker compose exec redis redis-cli FLUSHALL
```

See [backups.md](backups.md) for the full backup / restore workflow.

## After an import

The Wagtail search index (Solr) does not auto-rebuild after a bulk
update. Run:

```bash
docker compose exec web python manage.py update_index
```

The daily RDF export (see
[../developers/rdf-export.md](../developers/rdf-export.md)) will
pick up the new data on its next run automatically.
