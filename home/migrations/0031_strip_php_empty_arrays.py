"""
Empty out every Book TextField/CharField whose value is the PHP-
serialised empty array (``a:0:{}``) carried over from the Drupal-6
import. The rendered detail rows used to surface this noise as the
field value; the value_filters.clean_value filter handles it on the
display side, but emptying the DB itself keeps the field empty in
the Wagtail admin too.

The 0030 migration already strips legacy patterns from Person names;
this one targets the other half of the legacy junk — PHP
``serialize(array())`` empties — across every Book text column.
"""
from __future__ import annotations

import re

from django.db import migrations


_PHP_EMPTY_ARRAY = re.compile(r'^a:0:\{\}\s*;?\s*$')


def forwards(apps, schema_editor):
    Book = apps.get_model("home", "Book")
    text_fields = [
        f.name for f in Book._meta.fields
        if f.get_internal_type() in ("TextField", "CharField")
    ]
    cleaned = 0
    for b in Book.objects.all():
        updates = {}
        for fname in text_fields:
            v = getattr(b, fname, None) or ""
            if _PHP_EMPTY_ARRAY.match(v.strip()):
                updates[fname] = ""
        if updates:
            for fname, new in updates.items():
                setattr(b, fname, new)
            b.save(update_fields=list(updates))
            cleaned += 1
    if cleaned:
        print(f"  cleaned a:0:{{}} from {cleaned} Book rows")


def revert(apps, schema_editor):
    # Lossy migration — no way to restore the original "a:0:{}"
    # string per-row from an empty TextField. No-op so a backwards
    # migrate doesn't crash.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0030_clean_person_names"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=revert),
    ]
