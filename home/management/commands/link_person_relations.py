from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Book, Person, Translation, Preface, Production, Mention  # adjust


class Command(BaseCommand):
    help = "Link Books/Translations/Prefaces/Productions/Mentions to persons via the Drupal nid fields."

    @transaction.atomic
    def handle(self, *args, **options):
        # Person mapping: legacy_nid -> Person
        persons_by_legacy_nid = {
            p.legacy_nid: p
            for p in Person.objects.all().only("id", "legacy_nid")
        }
        self.stdout.write(f"{len(persons_by_legacy_nid)} persons in mapping.")

        # --- Books: original_text_author & old_text_author ---
        linked_original = linked_old = missing_original = missing_old = 0

        for book in Book.objects.all():
            # original_text_author
            if book.legacy_original_text_author_nid:
                person = persons_by_legacy_nid.get(book.legacy_original_text_author_nid)
                if person:
                    if book.original_text_author_id != person.id:
                        book.original_text_author = person
                        linked_original += 1
                else:
                    missing_original += 1

            # old_text_author
            if book.legacy_old_text_author_nid:
                person = persons_by_legacy_nid.get(book.legacy_old_text_author_nid)
                if person:
                    if book.old_text_author_id != person.id:
                        book.old_text_author = person
                        linked_old += 1
                else:
                    missing_old += 1

            # Save changes if there were any
            book.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Books: {linked_original} original_author, {linked_old} old_author linked; "
                f"{missing_original} / {missing_old} without matching person."
            )
        )

        # --- Translations: translator ---
        linked_translator = missing_translator = 0

        for tr in Translation.objects.all():
            if tr.legacy_translator_nid:
                person = persons_by_legacy_nid.get(tr.legacy_translator_nid)
                if person:
                    if tr.translator_id != person.id:
                        tr.translator = person
                        tr.save(update_fields=["translator"])
                        linked_translator += 1
                else:
                    missing_translator += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Translations: {linked_translator} translator linked, "
                f"{missing_translator} without matching person."
            )
        )

        # --- Prefaces: writer ---
        linked_writer = missing_writer = 0

        for pr in Preface.objects.all():
            if pr.legacy_preface_writer_nid:
                person = persons_by_legacy_nid.get(pr.legacy_preface_writer_nid)
                if person:
                    if pr.writer_id != person.id:
                        pr.writer = person
                        pr.save(update_fields=["writer"])
                        linked_writer += 1
                else:
                    missing_writer += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Prefaces: {linked_writer} writer linked, "
                f"{missing_writer} without matching person."
            )
        )

        # --- Productions: producer ---
        linked_producer = missing_producer = 0

        for prod in Production.objects.all():
            if prod.legacy_producer_nid:
                person = persons_by_legacy_nid.get(prod.legacy_producer_nid)
                if person:
                    if prod.producer_id != person.id:
                        prod.producer = person
                        prod.save(update_fields=["producer"])
                        linked_producer += 1
                else:
                    missing_producer += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Productions: {linked_producer} producer linked, "
                f"{missing_producer} without matching person."
            )
        )

        # --- Mentions: mentionee ---
        linked_mentionee = missing_mentionee = 0

        for m in Mention.objects.all():
            if m.legacy_mentionee_nid:
                person = persons_by_legacy_nid.get(m.legacy_mentionee_nid)
                if person:
                    if m.mentionee_id != person.id:
                        m.mentionee = person
                        m.save(update_fields=["mentionee"])
                        linked_mentionee += 1
                else:
                    missing_mentionee += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Mentions: {linked_mentionee} mentionee linked, "
                f"{missing_mentionee} without matching person."
            )
        )
