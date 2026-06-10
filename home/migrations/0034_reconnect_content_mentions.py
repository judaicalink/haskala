"""
Promote five remaining content-mention orphans into proper Mention
rows and set place_of_birth for the three persons whose toponymic
surname matches a historically-attested birthplace.

This migration finalises the orphan-cities sweep tracked in
``docs/audits/orphan_place_mentions.csv``. The Pränumeranten cohort
was handled by the ``reconnect_orphan_place_mentions`` management
command (PR #111). What is fixed here are the residual cases that
fell outside that command's per-field policy:

Mentions (description=NULL — no clean MentionDescription fits):

- Polen      (Book b01c1274 — "Die Juden Oder Die nothwendige
              Reformation der Juden in der Republik Polen")
- Hungary    (Book 08bacf86 — secondary_sources cites
              "Jewry … Hungary")
- Hirschberg (Book ff5dc661 — sources_references cites
              "Hirschberg a. Lissa")
- Florenz    (Book 756331fc — full_title carries
              "Art. Florenz den 20sten März")
- Arad       (Book 010c3164 — full_title carries
              "Synagogus in Arad R. Aaran Charin")

place_of_birth fills (historically attested):

- Salomon Dubno (1738-1813)        -> Dubno, Wolhynia
- Joseph Ephrati                   -> Troplowitz, Silesia

Skipped on purpose:

- Kiel — appears only as "Universitätsbibliothek Kiel / UB Kiel"
  library-shelfmark, not a content mention of the city.
- Lieben — appears only as the German word "Lieben (Brüder)" in
  target_audience_notes, not the Czech town Libeň.

Idempotent: each operation checks current state before writing, so
re-running the migration is a no-op.
"""
from __future__ import annotations

from django.db import migrations


MENTIONS = [
    # (book_pk, city_pk, city_name_for_log)
    (
        "b01c1274-e461-406f-a279-a7985f95316e",
        "45eaaa97-a334-4546-9c2c-cd1cd232a855",
        "Polen",
    ),
    (
        "08bacf86-347c-46fe-baec-9a89852e23f4",
        "d1474318-6cff-438b-99db-f1dbfb93f8e3",
        "Hungary",
    ),
    (
        "ff5dc661-1a95-4188-8f16-286f18bdd544",
        "310df71a-b23b-416c-875a-2ede37ffeb4d",
        "Hirschberg",
    ),
    (
        "756331fc-9f56-49f7-b539-2f776449592b",
        "9b248b36-c0d9-493e-a590-00a1cade9baa",
        "Florenz",
    ),
    (
        "010c3164-4956-48b8-96fb-a8280df1b2fc",
        "e8862065-19f4-47fd-8762-e1c6082e6b80",
        "Arad",
    ),
]

# Person pref_label substring -> City name (substring on City.name)
PLACE_OF_BIRTH = [
    ("Dubno, Salomon", "Dubno"),
    ("Troplowitz, Joseph Ephrati", "Troplowitz"),
]


def apply(apps, schema_editor):
    Book = apps.get_model("home", "Book")
    City = apps.get_model("home", "City")
    Mention = apps.get_model("home", "Mention")
    Person = apps.get_model("home", "Person")

    for book_pk, city_pk, _label in MENTIONS:
        book = Book.objects.filter(pk=book_pk).first()
        city = City.objects.filter(pk=city_pk).first()
        if book is None or city is None:
            continue
        exists = Mention.objects.filter(
            book=book,
            mentionee_city=city,
            mentionee_description__isnull=True,
        ).exists()
        if exists:
            continue
        Mention.objects.create(
            book=book,
            mentionee=None,
            mentionee_city=city,
            mentionee_description=None,
        )

    for surname_match, city_name in PLACE_OF_BIRTH:
        city = City.objects.filter(name=city_name).first()
        if city is None:
            continue
        qs = Person.objects.filter(
            pref_label__startswith=surname_match,
            place_of_birth__isnull=True,
        )
        for person in qs:
            person.place_of_birth = city
            person.save(update_fields=["place_of_birth"])


def revert(apps, schema_editor):
    City = apps.get_model("home", "City")
    Mention = apps.get_model("home", "Mention")
    Person = apps.get_model("home", "Person")

    for book_pk, city_pk, _label in MENTIONS:
        Mention.objects.filter(
            book_id=book_pk,
            mentionee_city_id=city_pk,
            mentionee_description__isnull=True,
        ).delete()

    for surname_match, city_name in PLACE_OF_BIRTH:
        city = City.objects.filter(name=city_name).first()
        if city is None:
            continue
        Person.objects.filter(
            pref_label__startswith=surname_match,
            place_of_birth=city,
        ).update(place_of_birth=None)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0033_populate_topic_occupation_slugs"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
