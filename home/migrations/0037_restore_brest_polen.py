"""
Restore the two City rows the operator accidentally deleted during
the Phase 2 manual-review pass, and anchor them to their Wikidata
QIDs.

  Brest  c6376e77-0fd9-428f-b73d-97551d6baaec  Q140147
  Polen  45eaaa97-a334-4546-9c2c-cd1cd232a855  Q36

Polen is semantically a country, not a city. It lives in the City
table for now because the catalog has no separate Country model;
a follow-up migration can promote it once that model exists. The
``wikidata_id=Q36`` anchor makes the distinction explicit until
then.

Idempotent — both rows are created via update_or_create so a
re-apply on a database where they already exist is a no-op.
"""
from __future__ import annotations

from django.db import migrations


RESTORES = [
    {
        "uuid": "c6376e77-0fd9-428f-b73d-97551d6baaec",
        "name": "Brest",
        "slug": "brest",
        "wikidata_id": "Q140147",
    },
    {
        "uuid": "45eaaa97-a334-4546-9c2c-cd1cd232a855",
        "name": "Polen",
        "slug": "polen",
        "wikidata_id": "Q36",
    },
]


def apply(apps, schema_editor):
    City = apps.get_model("home", "City")
    for row in RESTORES:
        City.objects.update_or_create(
            uuid=row["uuid"],
            defaults={
                "name": row["name"],
                "slug": row["slug"],
                "wikidata_id": row["wikidata_id"],
                "live": True,
            },
        )


def revert(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0036_remove_smoke_test_fixtures"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
