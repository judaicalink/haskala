"""
Hard-delete the smoke-/manual-test fixtures that leaked into the
production catalog while the public Book / Publisher / Places routes
were being wired up:

  Book      smokebibbook, testbook
  Publisher smokep,       testpub
  City      smokec

The rows are obvious throwaways (slugs literally contain the word
"smoke" / "test"). Hard-deleting them is safer than archiving via
live=False — these have no curated content to recover.

Idempotent: if a slug is already gone the filter returns nothing and
the operation is a no-op. The reverse migration is a no-op too — once
deleted, we don't fabricate the rows back.
"""
from __future__ import annotations

from django.db import migrations


SMOKE_BOOKS = ["smokebibbook", "testbook"]
SMOKE_PUBLISHERS = ["smokep", "testpub"]
SMOKE_CITIES = ["smokec"]


def apply(apps, schema_editor):
    Book = apps.get_model("home", "Book")
    Publisher = apps.get_model("home", "Publisher")
    City = apps.get_model("home", "City")
    Book.objects.filter(slug__in=SMOKE_BOOKS).delete()
    Publisher.objects.filter(slug__in=SMOKE_PUBLISHERS).delete()
    City.objects.filter(slug__in=SMOKE_CITIES).delete()


def revert(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0035_city_wikidata_fields"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
