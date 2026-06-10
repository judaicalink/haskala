"""
Materialize the in-text mentions catalogued by
``find_orphan_place_mentions`` as proper ``Mention`` rows so the
orphan cities cease to be unreferenced.

Per-field policy (kept conservative — we only touch fields whose
semantics are unambiguous):

- ``subscribers_notes``  -> Mention(description=Subscriber)
- ``mention_general_notes`` -> Mention(description=NULL)

All other fields (titles, references_notes, dedications_notes,
copy_of_book_used, ...) are reported but **not** auto-reconnected
because the right MentionDescription differs case-by-case. Use the
audit CSV as a worklist for those.

Idempotent: a Mention is only created if no row with the same
(book, mentionee_city, mentionee_description) tuple already exists.
Dry-run by default; pass ``--apply`` to commit.
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from home.models import Book, City, Mention, MentionDescription


# Maps the source field name to the MentionDescription slug we
# attach. ``None`` means "create a Mention without a description".
FIELD_POLICY = {
    "subscribers_notes": "Subscriber",
    "mention_general_notes": None,
}


class Command(BaseCommand):
    help = (
        "Create Mention rows for orphan cities discovered in "
        "Book.subscribers_notes / Book.mention_general_notes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="docs/audits/orphan_place_mentions.csv",
            help="Worklist CSV produced by find_orphan_place_mentions.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit the changes. Default: dry-run.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        apply = options["apply"]

        if not csv_path.exists():
            self.stderr.write(
                f"CSV not found at {csv_path}. "
                f"Run find_orphan_place_mentions first."
            )
            return

        descriptions = {
            md.name: md for md in MentionDescription.objects.all()
        }
        for slug in FIELD_POLICY.values():
            if slug is not None and slug not in descriptions:
                self.stderr.write(
                    f"Missing MentionDescription '{slug}'."
                )
                return

        # Collect unique (book_pk, city_pk, description_pk) triples
        # filtered to the fields the policy maps. The CSV may carry
        # multiple rows per triple (same city named twice in the same
        # field) — we dedup at this layer.
        triples = set()
        skipped_fields = {}
        unknown_books = []
        unknown_cities = []

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r["model"] != "Book":
                    continue
                field = r["field"]
                if field not in FIELD_POLICY:
                    skipped_fields[field] = skipped_fields.get(field, 0) + 1
                    continue
                desc_slug = FIELD_POLICY[field]
                desc = descriptions[desc_slug] if desc_slug else None

                book = Book.objects.filter(pk=r["entity_pk"]).first()
                if book is None:
                    unknown_books.append(r["entity_pk"])
                    continue
                city = City.objects.filter(pk=r["orphan_uuid"]).first()
                if city is None:
                    unknown_cities.append(r["orphan_uuid"])
                    continue
                triples.add((
                    str(book.pk),
                    str(city.pk),
                    desc.pk if desc else None,
                    desc.name if desc else None,
                ))

        to_create = []
        skipped_existing = 0
        sorted_triples = sorted(
            triples,
            key=lambda t: (t[0], t[1], t[2] or 0, t[3] or ""),
        )
        for book_pk, city_pk, desc_pk, desc_name in sorted_triples:
            exists = Mention.objects.filter(
                book_id=book_pk,
                mentionee_city_id=city_pk,
                mentionee_description_id=desc_pk,
            ).exists()
            if exists:
                skipped_existing += 1
                continue
            to_create.append((book_pk, city_pk, desc_pk, desc_name))

        for book_pk, city_pk, _desc_pk, desc_name in to_create:
            label = desc_name or "(no description)"
            self.stdout.write(
                f"book={book_pk}  city={city_pk}  description={label}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"Triples in scope: {len(triples)}"
        )
        self.stdout.write(
            f"  Already a Mention: {skipped_existing}"
        )
        self.stdout.write(
            f"  Would create: {len(to_create)}"
        )
        if skipped_fields:
            self.stdout.write(
                f"  Skipped (no policy for field): {dict(skipped_fields)}"
            )
        if unknown_books:
            self.stdout.write(
                f"  Skipped (book not found): {len(unknown_books)}"
            )
        if unknown_cities:
            self.stdout.write(
                f"  Skipped (city not found): {len(unknown_cities)}"
            )

        if not apply:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: would create {len(to_create)} Mention(s). "
                f"Re-run with --apply to commit."
            ))
            return

        with transaction.atomic():
            for book_pk, city_pk, desc_pk, _desc_name in to_create:
                Mention.objects.create(
                    book_id=book_pk,
                    mentionee_id=None,
                    mentionee_city_id=city_pk,
                    mentionee_description_id=desc_pk,
                )

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(to_create)} Mention row(s)."
        ))
