from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Book, Edition, Translation  # Pfade an dein Projekt anpassen


class Command(BaseCommand):
    help = "Verknüpft Editionen und Übersetzungen mit Büchern anhand der Drupal-nid (book_target_id)."

    @transaction.atomic
    def handle(self, *args, **options):
        # Mapping: legacy_nid -> Book
        book_by_legacy_nid = {
            b.legacy_nid: b
            for b in Book.objects.all().only("id", "legacy_nid")
        }
        self.stdout.write(f"{len(book_by_legacy_nid)} Books im Mapping.")

        # --- Editions ---
        editions = Edition.objects.all()
        linked_editions = 0
        missing_book_for_edition = 0

        for ed in editions:
            if ed.legacy_book_nid is None:
                continue

            book = book_by_legacy_nid.get(ed.legacy_book_nid)
            if not book:
                missing_book_for_edition += 1
                continue

            # nur setzen, wenn noch nicht gesetzt oder abweichend
            if ed.book_id != book.id:
                ed.book = book
                ed.save(update_fields=["book"])
                linked_editions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Editionen: {linked_editions} verknüpft, "
                f"{missing_book_for_edition} ohne passenden Book."
            )
        )

        # --- Translations ---
        translations = Translation.objects.all()
        linked_translations = 0
        missing_book_for_translation = 0

        for tr in translations:
            if tr.legacy_book_nid is None:
                continue

            book = book_by_legacy_nid.get(tr.legacy_book_nid)
            if not book:
                missing_book_for_translation += 1
                continue

            if tr.book_id != book.id:
                tr.book = book
                tr.save(update_fields=["book"])
                linked_translations += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Translations: {linked_translations} verknüpft, "
                f"{missing_book_for_translation} ohne passenden Book."
            )
        )
