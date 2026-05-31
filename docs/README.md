# Documentation

The Haskala documentation is split by audience.

| Tree                                 | For                                  |
| ------------------------------------ | ------------------------------------ |
| [users/](users/)                     | Researchers and lay readers          |
| [admins/](admins/)                   | Content editors (Wagtail admin)      |
| [developers/](developers/)           | Contributors and operators           |

## Conventions

- All documentation is written in English. Sources for the dataset itself
  may be in German, Hebrew, Yiddish or other languages of the corpus, but
  prose that addresses the audience above stays in English.
- Each Markdown file is short and single-topic; if a page grows past a
  few screens of reading, split it.
- When a code path moves or a configuration default changes, update the
  matching doc in the same PR.

## Doc index

### Users

- [Getting started](users/getting-started.md)
- [Detail pages](users/detail-pages.md)
- [Citations](users/citations.md)

### Admins

- [Wagtail admin tour](admins/wagtail-admin.md)
- [Data imports](admins/data-imports.md)
- [Revisions and versioning](admins/revisions.md)

### Developers

- [Local setup](developers/setup.md)
- [Architecture overview](developers/architecture.md)
- [Data model](developers/data-model.md)
- [Importer workflow](developers/importers.md)
- [RDF export](developers/rdf-export.md)
- [Contributing](developers/contributing.md)
