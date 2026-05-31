# Revisions and versioning

Books, Persons and Cities track an edit history. Every save through
the Wagtail admin creates a revision; previous versions can be
inspected and restored.

## Viewing history

1. Open the snippet edit view for the record you want to inspect
   (e.g. **Snippets → Book → My title**).
2. Look for the **History** tab in the page header (next to **Edit**).
3. Each entry lists the user, the timestamp and a summary of the
   change. Click an entry to see the field-by-field diff.

If the **History** tab is missing on a snippet, that model does not
yet mix in `RevisionMixin`. The currently versioned models are
Book, Person and City; Publisher, Series, Topic, Occupation and the
other vocab snippets save without revisions on purpose — their rows
are rename-only and there is little to revert.

## Reverting to an older version

From the History view, click **Review this revision** on the entry
you want. Wagtail shows the form pre-filled with that revision's
values. **Save** to write them back as a *new* revision. The
intermediate revisions stay in the history so the change is itself
reversible.

## What gets versioned

The revision records every editor-facing field on the model. Fields
that are not exposed in the form (the `*_format` partners, the
`legacy_*` provenance columns, system timestamps) are not part of
the diff but are still preserved in the database.

## Versioning vs draft state

Haskala intentionally does *not* use Wagtail's draft / published
workflow on these snippets. A save is immediately live. If you want
to stage a change for review before it appears on the site, use the
History view's diff and revert flow rather than draft mode.

## When the history is too long

The Revision table is append-only. If a single record collects
hundreds of trivial edits, a developer can run
`python manage.py revisions_purge --pages=false --days=90` from the
Wagtail core management commands to drop revisions older than 90
days. This is an admin-coordination task, not an editor one.
