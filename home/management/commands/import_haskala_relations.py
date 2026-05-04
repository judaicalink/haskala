"""
Import Edition, Translation, Mention, Preface and Production records from the
pre-processed Drupal CSV exports and link them to the related Book / Person /
City / Language / MentionDescription rows.

Source files (one CSV per node type):
    research/export/editions_for_django.csv
    research/export/translations_for_django.csv
    research/export/mentions_for_django.csv
    research/export/prefaces_for_django.csv
    research/export/productions_for_django.csv

For Mention, Preface and Production the link to the parent Book is not in the
per-node CSV but in Drupal's multi-value table:
    Database/field_data_field_book.csv

ProductionRole values are not their own Drupal vocabulary; the role TIDs live
in the Occupation vocabulary. This command seeds ProductionRole rows on the
fly. TranslationType is also seeded with the single value "translation".
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from home.models import (
    Book,
    City,
    Edition,
    Language,
    Mention,
    MentionDescription,
    Occupation,
    Person,
    Preface,
    Production,
    ProductionRole,
    Translation,
    TranslationType,
)


# ----------------------------- helpers --------------------------------------


def parse_int(value):
    if value is None:
        return None
    val = str(value).strip()
    if val == "":
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


def parse_bool(value):
    val = str(value or "").strip().lower()
    return val in ("1", "true", "yes", "y", "t")


def parse_timestamp(value):
    val = str(value or "").strip()
    if not val:
        return None
    try:
        ts = float(val)
    except ValueError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.get_current_timezone())


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


# ------------------------ command implementation ----------------------------


class Command(BaseCommand):
    help = (
        "Import Edition, Translation, Mention, Preface and Production records "
        "and link them to existing Book / Person / City rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--export-dir",
            required=True,
            help=(
                "Directory holding the pre-processed CSV exports "
                "(editions_for_django.csv, translations_for_django.csv, ...). "
                "Typically research/export."
            ),
        )
        parser.add_argument(
            "--drupal-dir",
            required=True,
            help=(
                "Directory holding the raw Drupal CSV exports "
                "(used for field_data_field_book.csv). "
                "Typically Database."
            ),
        )

    # -- caches built in handle() -------------------------------------------

    def _book_by_nid(self):
        return {
            b.legacy_nid: b
            for b in Book.objects.exclude(legacy_nid__isnull=True).only(
                "uuid", "legacy_nid"
            )
        }

    def _person_by_nid(self):
        return {
            p.legacy_nid: p
            for p in Person.objects.exclude(legacy_nid__isnull=True).only(
                "uuid", "legacy_nid"
            )
        }

    def _city_by_tid(self):
        return {
            c.legacy_tid: c
            for c in City.objects.exclude(legacy_tid__isnull=True).only(
                "uuid", "legacy_tid"
            )
        }

    def _mention_description_by_tid(self):
        return {
            m.legacy_tid: m
            for m in MentionDescription.objects.exclude(legacy_tid__isnull=True)
        }

    def _book_backlink(self, drupal_dir: Path):
        """
        Build {sub_node_nid -> book_nid} from field_data_field_book.csv,
        used by Mention, Preface and Production where the per-node CSV does
        not carry the book link directly.
        """
        path = drupal_dir / "field_data_field_book.csv"
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        mapping: dict[int, int] = {}
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                child = parse_int(row.get("entity_id"))
                book = parse_int(row.get("field_book_target_id"))
                if child is None or book is None:
                    continue
                # delta=0 wins (first link); ignore later deltas
                mapping.setdefault(child, book)
        return mapping

    # -- imports -------------------------------------------------------------

    def import_editions(self, export_dir: Path):
        path = export_dir / "editions_for_django.csv"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Skipping editions: {path} not found."))
            return

        books = self._book_by_nid()
        cities = self._city_by_tid()
        created = updated = missing_book = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_nid = parse_int(row.get("nid"))
                if legacy_nid is None:
                    continue

                book_nid = parse_int(row.get("book_target_id"))
                book = books.get(book_nid) if book_nid else None
                if book is None:
                    missing_book += 1
                    continue

                defaults = {
                    "legacy_vid": parse_int(row.get("vid")),
                    "legacy_status": parse_bool(row.get("status")),
                    "legacy_created": parse_timestamp(row.get("created")),
                    "legacy_changed": parse_timestamp(row.get("changed")),
                    "name": clean(row.get("title")) or None,
                    "book": book,
                    "city": cities.get(parse_int(row.get("edition_city_tid"))),
                    "changes": clean(row.get("edition_changes")) or None,
                    "changes_format": clean(row.get("edition_changes_format")) or "NULL",
                    "references": clean(row.get("edition_references")) or None,
                    "references_format": clean(row.get("edition_references_format")) or "NULL",
                    "year": clean(row.get("edition_year")) or None,
                    "year_format": clean(row.get("edition_year_format")) or "NULL",
                }
                _, created_flag = Edition.objects.update_or_create(
                    legacy_nid=legacy_nid, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Edition: {created} created, {updated} updated, {missing_book} skipped (book missing)."
        ))

    def import_translations(self, export_dir: Path):
        path = export_dir / "translations_for_django.csv"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Skipping translations: {path} not found."))
            return

        # Drupal only ever uses one type ("translation"); seed it.
        TranslationType.objects.get_or_create(name="translation")

        books = self._book_by_nid()
        persons = self._person_by_nid()
        cities = self._city_by_tid()
        created = updated = missing_book = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_nid = parse_int(row.get("nid"))
                if legacy_nid is None:
                    continue

                book_nid = parse_int(row.get("book_target_id"))
                book = books.get(book_nid) if book_nid else None
                if book is None:
                    missing_book += 1
                    continue

                defaults = {
                    "legacy_vid": parse_int(row.get("vid")),
                    "legacy_status": parse_bool(row.get("status")),
                    "legacy_created": parse_timestamp(row.get("created")),
                    "legacy_changed": parse_timestamp(row.get("changed")),
                    "book": book,
                    "translator": persons.get(parse_int(row.get("translator_target_id"))),
                    "city": cities.get(parse_int(row.get("translation_city_tid"))),
                    "references": clean(row.get("translation_references")) or None,
                    "references_format": clean(row.get("translation_references_format")) or "NULL",
                    "year": clean(row.get("translation_year")),
                    "year_format": clean(row.get("translation_year_format")) or "NULL",
                    # Note: `title` from CSV is not stored - the Translation
                    # model has no title field yet.
                }
                _, created_flag = Translation.objects.update_or_create(
                    legacy_nid=legacy_nid, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Translation: {created} created, {updated} updated, {missing_book} skipped (book missing)."
        ))

    def import_mentions(self, export_dir: Path):
        path = export_dir / "mentions_for_django.csv"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Skipping mentions: {path} not found."))
            return

        persons = self._person_by_nid()
        cities = self._city_by_tid()
        descriptions = self._mention_description_by_tid()
        created = updated = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_nid = parse_int(row.get("nid"))
                if legacy_nid is None:
                    continue

                defaults = {
                    "legacy_vid": parse_int(row.get("vid")),
                    "legacy_status": parse_bool(row.get("status")),
                    "legacy_created": parse_timestamp(row.get("created")),
                    "legacy_changed": parse_timestamp(row.get("changed")),
                    "mentionee": persons.get(parse_int(row.get("mentionee_target_id"))),
                    "mentionee_city": cities.get(parse_int(row.get("mentionee_city_tid"))),
                    "mentionee_description": descriptions.get(
                        parse_int(row.get("mentionee_description_tid"))
                    ),
                }
                _, created_flag = Mention.objects.update_or_create(
                    legacy_nid=legacy_nid, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Mention: {created} created, {updated} updated."
        ))

    def import_prefaces(self, export_dir: Path, book_backlink: dict[int, int]):
        path = export_dir / "prefaces_for_django.csv"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Skipping prefaces: {path} not found."))
            return

        books = self._book_by_nid()
        persons = self._person_by_nid()
        created = updated = without_book = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_nid = parse_int(row.get("nid"))
                if legacy_nid is None:
                    continue

                book_nid = book_backlink.get(legacy_nid)
                book = books.get(book_nid) if book_nid else None
                if book is None:
                    without_book += 1

                defaults = {
                    "legacy_vid": parse_int(row.get("vid")),
                    "legacy_status": parse_bool(row.get("status")),
                    "legacy_created": parse_timestamp(row.get("created")),
                    "legacy_changed": parse_timestamp(row.get("changed")),
                    "book": book,
                    "writer": persons.get(parse_int(row.get("preface_writer_target_id"))),
                    "title": clean(row.get("preface_title")) or None,
                    "title_format": clean(row.get("preface_title_format")) or "NULL",
                    "notes": clean(row.get("preface_notes")) or None,
                    "notes_format": clean(row.get("preface_notes_format")) or "NULL",
                    "number": parse_int(row.get("preface_number")),
                    "number_format": clean(row.get("preface_number_format")) or "NULL",
                }
                _, created_flag = Preface.objects.update_or_create(
                    legacy_nid=legacy_nid, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Preface: {created} created, {updated} updated, {without_book} without book link."
        ))

    def import_productions(self, export_dir: Path, book_backlink: dict[int, int]):
        path = export_dir / "productions_for_django.csv"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Skipping productions: {path} not found."))
            return

        books = self._book_by_nid()
        persons = self._person_by_nid()
        created = updated = without_book = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_nid = parse_int(row.get("nid"))
                if legacy_nid is None:
                    continue

                book_nid = book_backlink.get(legacy_nid)
                book = books.get(book_nid) if book_nid else None
                if book is None:
                    without_book += 1

                role = self._resolve_production_role(parse_int(row.get("role_tid")))

                defaults = {
                    "legacy_vid": parse_int(row.get("vid")),
                    "legacy_status": parse_bool(row.get("status")),
                    "legacy_created": parse_timestamp(row.get("created")),
                    "legacy_changed": parse_timestamp(row.get("changed")),
                    "title": clean(row.get("title")) or None,
                    "book": book,
                    "producer": persons.get(parse_int(row.get("producer_target_id"))),
                    "role": role,
                }
                _, created_flag = Production.objects.update_or_create(
                    legacy_nid=legacy_nid, defaults=defaults
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Production: {created} created, {updated} updated, {without_book} without book link."
        ))

    def _resolve_production_role(self, role_tid):
        """
        Production roles reuse the Occupation vocabulary (vid=6 in Drupal).
        Seed ProductionRole rows on demand from the matching Occupation.
        """
        if role_tid is None:
            return None
        try:
            return ProductionRole.objects.get(legacy_tid=role_tid)
        except ProductionRole.DoesNotExist:
            pass

        try:
            occ = Occupation.objects.get(legacy_tid=role_tid)
        except Occupation.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f"role_tid={role_tid}: no matching Occupation; ProductionRole left unset."
            ))
            return None

        role, _ = ProductionRole.objects.get_or_create(
            legacy_tid=role_tid,
            defaults={"name": occ.name},
        )
        return role

    # -- entry point ---------------------------------------------------------

    @transaction.atomic
    def handle(self, *args, **options):
        export_dir = Path(options["export_dir"])
        drupal_dir = Path(options["drupal_dir"])

        if not export_dir.is_dir():
            raise CommandError(f"--export-dir is not a directory: {export_dir}")
        if not drupal_dir.is_dir():
            raise CommandError(f"--drupal-dir is not a directory: {drupal_dir}")

        book_backlink = self._book_backlink(drupal_dir)
        self.stdout.write(f"{len(book_backlink)} sub-node->book links available.")

        # Order matters: editions and translations first (they only need books),
        # then mentions/prefaces/productions which use book_backlink.
        self.import_editions(export_dir)
        self.import_translations(export_dir)
        self.import_mentions(export_dir)
        self.import_prefaces(export_dir, book_backlink)
        self.import_productions(export_dir, book_backlink)

        self.stdout.write(self.style.SUCCESS("Relation import finished."))
