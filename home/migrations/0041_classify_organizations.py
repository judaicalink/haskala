"""
Tag the 11 Person rows that the curator confirmed represent
organizations (societies, schools, libraries, publishing houses,
editorial boards) rather than humans, so the upcoming Wikidata
enrichment skips them and the public-site + RDF output can render
them as ``foaf:Organization`` / ``schema:Organization``.

Source: docs/audits/person_data_quality.md plus the curator's
manual review pass. Identified by exact ``pref_label`` match;
update_or_create-style upsert handles re-runs safely.

Idempotent: a row whose entity_type is already "organization"
stays that way; non-matching rows are left untouched.
"""
from __future__ import annotations

from django.db import migrations


ORGANIZATION_LABELS = [
    "Direktion der Kaufmännischen Ressource",
    "Gesellschaft der Freunde",
    "Gesellschaft der hebräischen Litteraturfreunde",
    "Gesellschaft des Guten und Edlen - חברת שוחרי הטוב והתושיה",
    "Israelitische Haupt- und Freischule zu Deßaus",
    "Jacobys Buchhandlung",
    "Konsistorium der Israeliten",
    "Redaktion der \"Sulamith\"",
    "Museum des Herrn Werkmeister",
    "Waisenhaus in Berlin und Halle",
    "Wallenrodtsche Bibliothek",
]


def apply(apps, schema_editor):
    Person = apps.get_model("home", "Person")
    Person.objects.filter(pref_label__in=ORGANIZATION_LABELS).update(
        entity_type="organization",
    )


def revert(apps, schema_editor):
    Person = apps.get_model("home", "Person")
    Person.objects.filter(pref_label__in=ORGANIZATION_LABELS).update(
        entity_type="person",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0040_person_entity_type"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
