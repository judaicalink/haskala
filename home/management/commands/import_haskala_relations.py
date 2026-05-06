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

Multi-value Book taxonomy links (one row per assignment):
    research/export/main_textual_models.csv
    research/export/secondary_textual_models.csv

Book.authors (BookAuthor through table) is materialized from three sources:
    - books_for_django.csv columns old_text_author_target_id and
      original_text_author_target_id (one Person per role per book)
    - the producer FK on already-imported Production rows
The role values match BookAuthor.role choices: old_text_author,
original_text_author, producer.

For Mention, Preface and Production the link to the parent Book is not in the
per-node CSV but in Drupal's multi-value table:
    Database/field_data_field_book.csv

ProductionRole values are not their own Drupal vocabulary; the role TIDs live
in the Occupation vocabulary. This command seeds ProductionRole rows on the
fly from the matching Occupation name.
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from home.models import (
    Book,
    BookAuthor,
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
    TextualModel,
    Translation,
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
                    "title": clean(row.get("title")),
                    "book": book,
                    "translator": persons.get(parse_int(row.get("translator_target_id"))),
                    "city": cities.get(parse_int(row.get("translation_city_tid"))),
                    "references": clean(row.get("translation_references")) or None,
                    "references_format": clean(row.get("translation_references_format")) or "NULL",
                    "year": clean(row.get("translation_year")),
                    "year_format": clean(row.get("translation_year_format")) or "NULL",
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
                    "name_in_book": clean(row.get("name_in_book")),
                    "person_name_appear": clean(row.get("person_name_appear")),
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

    def import_textual_model_links(self, export_dir: Path):
        """
        Populate the Book.main_textual_models and Book.secondary_textual_models
        ManyToMany relations from Drupal's multi-value tables. The per-book CSV
        only carries a single TID per field (the first delta), so we treat the
        relation tables as authoritative and overwrite the M2M sets here.
        """
        sources = [
            ("main", "main_textual_models.csv", "main_textual_models"),
            ("secondary", "secondary_textual_models.csv", "secondary_textual_models"),
        ]

        books = self._book_by_nid()
        models_by_tid = {
            t.legacy_tid: t
            for t in TextualModel.objects.exclude(legacy_tid__isnull=True)
        }

        for label, filename, m2m_attr in sources:
            path = export_dir / filename
            if not path.exists():
                self.stdout.write(self.style.WARNING(
                    f"Skipping {label} textual models: {path} not found."
                ))
                continue

            grouped: dict[int, list[TextualModel]] = {}
            unknown_tids = set()
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    nid = parse_int(row.get("nid"))
                    tid = parse_int(row.get("tid"))
                    if nid is None or tid is None:
                        continue
                    tm = models_by_tid.get(tid)
                    if tm is None:
                        unknown_tids.add(tid)
                        continue
                    grouped.setdefault(nid, []).append(tm)

            updated = without_book = total_links = 0
            for nid, tms in grouped.items():
                book = books.get(nid)
                if book is None:
                    without_book += 1
                    continue
                getattr(book, m2m_attr).set(tms)
                updated += 1
                total_links += len(tms)

            msg = (
                f"{label.capitalize()} textual models: {updated} books linked, "
                f"{total_links} M2M rows, {without_book} without book."
            )
            if unknown_tids:
                msg += f" Unknown TIDs skipped: {sorted(unknown_tids)}."
            self.stdout.write(self.style.SUCCESS(msg))

    def import_book_authors(self, export_dir: Path):
        """
        Materialize Book.authors (through BookAuthor) from:
        - books_for_django.csv columns old_text_author_target_id and
          original_text_author_target_id;
        - existing Production rows (book + producer) for the producer role.

        BookAuthor has no DB-level uniqueness, so we wipe and rebuild to keep
        the import idempotent.
        """
        books = self._book_by_nid()
        persons = self._person_by_nid()

        seen: set[tuple] = set()
        rows: list[BookAuthor] = []
        unknown_persons = 0

        # 1) Text-author roles from the books CSV
        path = export_dir / "books_for_django.csv"
        if path.exists():
            csv_role_columns = [
                ("old_text_author_target_id", "old_text_author"),
                ("original_text_author_target_id", "original_text_author"),
            ]
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    book = books.get(parse_int(row.get("nid")))
                    if book is None:
                        continue
                    for col, role in csv_role_columns:
                        pid = parse_int(row.get(col))
                        if pid is None:
                            continue
                        person = persons.get(pid)
                        if person is None:
                            unknown_persons += 1
                            continue
                        key = (book.uuid, person.uuid, role)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(BookAuthor(
                            book_id=book.uuid, person_id=person.uuid, role=role,
                        ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Skipping text-author roles: {path} not found."
            ))

        # 2) Producer role from already-imported Production rows
        producer_pairs = Production.objects.filter(
            book__isnull=False, producer__isnull=False,
        ).values_list("book_id", "producer_id")
        for book_id, person_id in producer_pairs:
            key = (book_id, person_id, "producer")
            if key in seen:
                continue
            seen.add(key)
            rows.append(BookAuthor(
                book_id=book_id, person_id=person_id, role="producer",
            ))

        BookAuthor.objects.all().delete()
        BookAuthor.objects.bulk_create(rows)

        per_role = {}
        for r in rows:
            per_role[r.role] = per_role.get(r.role, 0) + 1
        self.stdout.write(self.style.SUCCESS(
            f"BookAuthor: {len(rows)} rows ({per_role}); "
            f"{unknown_persons} CSV target_ids without matching Person."
        ))

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
        self.import_textual_model_links(export_dir)
        self.import_book_authors(export_dir)

        self.stdout.write(self.style.SUCCESS("Relation import finished."))
