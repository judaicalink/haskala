"""
Mark every City with zero references as ``live=False`` so it
disappears from the public site without losing the row. Recoverable —
flipping the row back to ``live=True`` un-archives it.

Use this after ``audit_data_quality`` has confirmed the orphan list
matches the expected output. Dry-run by default.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import (
    Book, City, Edition, Mention, Person, Translation,
)


def is_orphan(c: City) -> bool:
    if Book.objects.filter(
        Q(publication_place=c)
        | Q(publication_place_other=c)
        | Q(original_publication_place=c)
    ).exists():
        return False
    if Person.objects.filter(
        Q(place_of_birth=c) | Q(place_of_death=c)
    ).exists():
        return False
    if Edition.objects.filter(city=c).exists():
        return False
    if Translation.objects.filter(city=c).exists():
        return False
    if Mention.objects.filter(mentionee_city=c).exists():
        return False
    return True


class Command(BaseCommand):
    help = "Set live=False on every City that no other record references."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit the changes. Default: dry-run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        orphans = [c for c in City.objects.filter(live=True) if is_orphan(c)]

        for c in orphans:
            self.stdout.write(f"{c.pk}  {c.name!r}  -> live=False")

        if not apply:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: would set live=False on {len(orphans)} "
                f"orphan cities. Re-run with --apply to commit."
            ))
            return

        for c in orphans:
            c.live = False
            c.save(update_fields=["live"])
        self.stdout.write(self.style.SUCCESS(
            f"Marked {len(orphans)} orphan cities as draft (live=False)."
        ))
