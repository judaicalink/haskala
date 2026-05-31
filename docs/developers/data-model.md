# Data model

The catalogue lives in `home/models.py`. The model has accreted over
years of import + correction passes, so this page summarises the
shape rather than listing every field.

## Primary entities

### Book

The richest record in the dataset, with about 270 fields. Use the
section list in [`home/book_detail.py`](../../home/book_detail.py)
as the canonical grouping; the Wagtail edit form
(`home/book_admin.py`) uses the same groupings.

Important attributes:

- `name` — used as the URL slug. Persisted as `TextField`, which is
  unusual; this is a legacy of the original Drupal import.
- `bundle` — a discriminator on `BUNDLE_CHOICES`
  (`book`, `translation`, `edition`, `mention`, `preface`,
  `production`). The RDF exporter emits this as an extra `rdf:type`.
- `authors` — a `ManyToManyField(Person, through=BookAuthor)`. The
  through-model carries the role.
- Foreign keys to `Publisher`, `City` (publication_place), `Series`,
  `Topic`, `Language`, `Alignment`, `OriginalType`,
  `TranslationType`, `FormatOfPublicationDate`, `LanguageCount`,
  `FootnoteLocation`.
- Reverse relations: `bookauthor_set`, `editions`, `translations`,
  `prefaces`, `productions`, `mentions`.

### Person

Authors, editors, subscribers, mentioned figures. Primary identifier
is `uuid`. Carries `pref_label`, `german_name`, `hebrew_name`,
`pseudonym`, `gender`, `occupations` (M2M), `date_of_birth`,
`date_of_death`, `place_of_birth`, `place_of_death`, `viaf_id`.

### City

The vocabulary for places. Carries `name` and an optional
`Geolocation` (`lat`/`lng`) for the Leaflet map. Persons link to
cities through `place_of_birth` / `place_of_death`; books through
`publication_place` / `publication_place_other` /
`original_publication_place`; editions and translations via their
own `city` FK; mentions via `mentionee_city`.

## Vocabulary snippets

| Snippet                  | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `Publisher`              | Publishing houses                                       |
| `Series`                 | Multi-volume series                                     |
| `Topic`                  | Subject taxonomy                                        |
| `Occupation`             | Professions                                             |
| `Gender`                 | Gender categories                                       |
| `Language`               | Languages of the corpus                                 |
| `Font`                   | Typefaces                                               |
| `Typography`             | Typography descriptors                                  |
| `Alignment`              | Religious / cultural alignment                          |
| `TextualModel`           | Genre / model categories                                |
| `TargetAudience`         | Audience descriptors                                    |
| `OriginalType`           | Source-type categories                                  |
| `TranslationType`        | Translation type vocabulary                             |
| `FootnoteLocation`       | Where footnotes appear                                  |
| `LanguageCount`          | Coarse language-count buckets                           |
| `DateFormat`             | Calendar / format descriptors                           |

## Through and link models

- `BookAuthor` — joins Book ↔ Person with a `role` choice
  (`old_text_author`, `original_text_author`, `producer`).
- `Edition` — a known edition of a Book, with `year`, `city`,
  `changes`.
- `Translation` — a known translation, with `language`, `translator`,
  `city`, `year`.
- `Preface` — a preface in a book, with `number`, `title`, `writer`.
- `Production` — a printing-side participant, with `producer` and
  `role` (a `ProductionRole`).
- `Mention` — a mention of a Person in a Book, with optional
  `mentionee_city` and `mentionee_description` (`MentionDescription`).

## Legacy-import provenance

`LegacyImportedModel` is the abstract base for everything that came
from the Drupal source. It carries `legacy_nid`, `legacy_vid`,
`legacy_language`, `legacy_status`, `legacy_created`,
`legacy_changed`. The importers match rows by `legacy_nid` /
`legacy_tid` on re-runs, so these columns stay populated; the
public site surfaces them only in the "Record metadata" section.

## Versioning

`Book`, `Person` and `City` mix in Wagtail's `RevisionMixin`. Every
save through the admin form writes a revision. Migration `0023_…`
added the `latest_revision` FK. Other models version-control via
their controlled-vocabulary nature — a rename is rare and easy to
audit in git history.

## URL slugs

- Book → `name` (TextField). Spaces and Unicode survive into URLs.
- Person → `uuid` (the primary key).
- City → `slugify(name)`. Names that slugify to empty (Hebrew-only)
  are guarded in the list templates so the page does not 500.
- Publisher / Series → `slug` field on the model, auto-filled by
  `save()` from `name` on first save.
- Topic / Occupation → `slugify(name)` at request time.
