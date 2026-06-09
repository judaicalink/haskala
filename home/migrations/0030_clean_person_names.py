"""
Data migration that runs the Person-name cleaner over every row.

The same regex pipeline that ``manage.py clean_person_names`` uses,
inlined here so a freshly-seeded database (from
``data/initial/haskala.sql`` or from a Drupal-6 dump) automatically
loses the legacy ``(Dr. med.) NAME`` and ``"NAME"`` patterns + any
leading punctuation. Idempotent — a clean row stays clean.

Originally a manual command in PR #67; promoted to a migration so
the fix survives a DB rebuild and travels with every commit instead
of needing a remember-to-run-this step.
"""
from __future__ import annotations

import re

from django.db import migrations


_PARENS_PREFIX = re.compile(r"^\([^)]*\)\s*")
_QUOTE_WRAP = re.compile(r'^"(.*)"$')
_LEADING_JUNK = re.compile(r"^[\s,.;:'\"\-]+")
_MULTI_WS = re.compile(r"\s{2,}")


def _clean(value):
    if not value:
        return value
    out = value
    out = _PARENS_PREFIX.sub("", out)
    m = _QUOTE_WRAP.match(out)
    if m:
        out = m.group(1)
    out = _LEADING_JUNK.sub("", out)
    out = _MULTI_WS.sub(" ", out).strip()
    return out


def forwards(apps, schema_editor):
    Person = apps.get_model("home", "Person")
    fields = ("pref_label", "german_name", "hebrew_name")
    for p in Person.objects.all():
        updates = {}
        for fname in fields:
            current = getattr(p, fname, "") or ""
            new = _clean(current)
            if new != current:
                updates[fname] = new
        if updates:
            for fname, new in updates.items():
                setattr(p, fname, new)
            p.save(update_fields=list(updates))


def revert(apps, schema_editor):
    # Cleaning is destructive — re-running the migration backwards
    # can't reproduce the dropped "(Dr. med.) " / "\"...\"" wrappers.
    # No-op so a backwards migrate doesn't blow up.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0029_regenerate_slugs_strip_non_latin"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=revert),
    ]
