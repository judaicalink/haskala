# Wagtail admin tour

This page is for content editors who need to add, correct or remove
records via the web UI.

## Logging in

The admin is at <http://localhost:8080/admin/> in dev, and at
`https://<host>/admin/` in production. A superuser is created with:

```bash
docker compose exec web python manage.py createsuperuser
```

## Where to find things

The left-hand sidebar groups everything into:

- **Books** — the catalogue. Use the search field at the top for
  free-text matches across title, author name (in Latin and Hebrew
  script) and the bundle ("translation", "edition", …).
- **Snippets** — every other editable record. The most frequently
  edited:

  | Snippet              | What it holds                                                  |
  | -------------------- | -------------------------------------------------------------- |
  | Person               | Authors, editors, translators, subscribers                     |
  | City                 | Places of publication, birth, death                            |
  | Publisher            | Houses and presses                                             |
  | Series               | Multi-volume series titles                                     |
  | Edition / Translation| Children of a Book                                             |
  | Preface / Production | Children of a Book                                             |
  | Mention              | A person mentioned in a book                                   |
  | BookAuthor           | Joins a Book to a Person with a role (old-text / original /
                          producer)                                                       |
  | Topic, Occupation, Gender, Language, Font, Typography, …
                         | Controlled-vocabulary terms used by the records above          |

- **Pages** — the small set of static pages and the home page; only
  editors who maintain prose need to touch this.

## Editing a Book

A Book opens with a long form split into collapsible sections that
mirror the public detail page (Basics, Identity & titles, Authors &
persons, Publication, Physical & typography, …). Open the section you
need, edit the values, and use **Save** at the bottom.

- **Basics** stays open by default and carries `name`, `full_title`,
  and `bundle`.
- Fields whose name ends in `_format` are *not* shown in the form;
  they record which markup language a long text field uses and are
  set by the importers. Edit the text field itself, not its format
  partner.

## Editing relations

Author rows on a Book are stored as **BookAuthor** snippets, not on
the Book form itself. To add a new author:

1. Open the **Snippets → BookAuthor** list.
2. Click **Add a BookAuthor**.
3. Pick the Book, the Person, and the role.
4. Save.

The author then appears in the Book's hero chip strip and in the
Authors & Persons section.

A future iteration may bring this in-line on the Book form; for now
the separate snippet is the canonical edit point.

## Saving and revisions

Every save on a Book, Person or City creates a revision. See
[revisions.md](revisions.md) for how to view history and revert.

## Permissions

The admin honours Django's standard permission system:

- **Superusers** can do anything.
- **Editors** should be added to a group with `add`, `change` and
  `view` permissions on the snippets above. They should not need
  `delete`.
- **Readers** with only `view` permission can use the admin as a
  data-quality tool without risking accidental edits.

Create groups in **Settings → Groups** and assign users in
**Settings → Users**.
