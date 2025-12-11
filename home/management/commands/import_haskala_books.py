import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models as dj_models
from django.utils import timezone

from home.models import (
    Book,
    Alignment,
    Font,
    Language,
    LanguageCount,
    FootnoteLocation,
    TextualModel,
    TargetAudience,
    Typography,
    City,
    Publisher,
    DateFormat,
    OriginalType,
    Topic,
)


def parse_int(value):
    if value is None:
        return None
    val = str(value).strip()
    if val == "":
        return None
    try:
        # viele TIDs kamen als '402.0' etc.
        return int(float(val))
    except ValueError:
        return None


def parse_bool(value):
    val = str(value).strip()
    if val in ("1", "true", "True", "yes", "Yes"):
        return True
    if val in ("0", "false", "False", "no", "No", ""):
        return False
    return False


def parse_timestamp(value):
    """
    Drupal stored created/changed usually as UNIX timestamp (int).
    """
    if value is None:
        return None

    val = str(value).strip()
    if val == "":
        return None

    try:
        ts = float(val)
    except ValueError:
        return None

    # aktuelle Zeitzone von Django verwenden (Europe/Berlin bei dir)
    tz = timezone.get_current_timezone()
    return datetime.fromtimestamp(ts, tz=tz)


def parse_tid_list(value):
    """
    Falls später mehrere TIDs (z.B. '12|34') kommen, sind wir vorbereitet.
    Im Moment erwarten wir meist einen einzelnen Wert.
    """
    if value is None:
        return []
    val = str(value).strip()
    if val == "":
        return []
    parts = [p for p in val.replace(" ", "").split("|") if p]
    tids = []
    for p in parts:
        tid = parse_int(p)
        if tid is not None:
            tids.append(tid)
    return tids


class Command(BaseCommand):
    help = "Importiert Haskala-Bücher aus der CSV-Datei books_for_django.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Pfad zur CSV-Datei (books_for_django.csv)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])
        if not csv_path.exists():
            raise CommandError(f"Datei nicht gefunden: {csv_path}")

        self.stdout.write(f"Lese Datei: {csv_path}")

        created_count = 0
        updated_count = 0

        # vorbereiten: einfache Felder im Book-Modell (ohne FK/M2M)
        simple_fields = {
            f.name: f
            for f in Book._meta.get_fields()
            if isinstance(f, dj_models.Field)
            and not f.many_to_many
            and not f.one_to_many
            and not isinstance(f, dj_models.ForeignKey)
        }

        # Felder, die wir für Legacy-Metadaten und interne Dinge manuell setzen
        exclude_auto = {
            "uuid",
            "created_at",
            "updated_at",
            "legacy_nid",
            "legacy_vid",
            "legacy_language",
            "legacy_status",
            "legacy_created",
            "legacy_changed",
        }

        for name in exclude_auto:
            simple_fields.pop(name, None)

        # Mapping von CSV-Spaltennamen auf Book-Feldnamen (wenn unterschiedlich)
        rename_map = {
            "title": "name",
            "book_availability_notes": "availability_notes",
            "book_availability_notes_format": "availability_notes_format",
            "book_not_available": "not_available",
            "book_structure_notes": "structure_notes",
            "book_structure_notes_format": "structure_notes_format",
            "book_studies": "studies",
            "book_studies_format": "studies_format",
            "book_type_general_notes": "type_general_notes",
            "book_type_general_notes_format": "type_general_notes_format",
            "link_to_digital_book_url": "digital_book_url",
            "link_to_digital_book_attributes": "digital_book_attributes",
            "link_to_digital_book_title": "digital_book_title",
            "link_to_digital_book_url_format": "digital_book_url_format",
            "publication_year_in_book": "year_in_book",
            "publication_year_in_book_format": "year_in_book_format",
            "publication_year_in_other": "year_in_other",
            "publication_year_in_other_format": "year_in_other_format",
        }

        # alle relevanten *_tid Spalten, die wir speziell behandeln
        fk_tid_fields = {
            "alignment_tid": (Alignment, "alignment"),
            "languages_number_tid": (LanguageCount, "languages_number"),
            "format_of_publication_date_tid": (DateFormat, "format_of_publication_date"),
            "location_of_footnotes_tid": (FootnoteLocation, "location_of_footnotes"),
            "original_language_tid": (Language, "original_language"),
            "original_publication_place_tid": (City, "original_publication_place"),
            "original_publisher_tid": (Publisher, "original_publisher"),
            "publication_place_tid": (City, "publication_place"),
            "publication_place_other_tid": (City, "publication_place_other"),
            "publisher_name_tid": (Publisher, "publisher"),
            "original_type_tid": (OriginalType, "original_type"),
            "topic_tid": (Topic, "topic"),
        }

        m2m_tid_fields = {
            "fonts_tid": (Font, "fonts"),
            "language_tid": (Language, "languages"),
            "language_of_footnotes_tid": (Language, "footnote_languages"),
            "occasional_words_languages_tid": (Language, "occasional_words_languages"),
            "main_textual_models_tid": (TextualModel, "main_textual_models"),
            "secondary_textual_models_tid": (TextualModel, "secondary_textual_models"),
            "target_audience_tid": (TargetAudience, "target_audience"),
            "typography_tid": (Typography, "typography"),
        }

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            with transaction.atomic():
                for row in reader:
                    # --- Legacy IDs ---
                    legacy_nid = parse_int(row.get("nid"))
                    legacy_vid = parse_int(row.get("vid"))

                    if legacy_nid is None:
                        self.stdout.write(
                            self.style.WARNING("Zeile ohne gültige nid – übersprungen.")
                        )
                        continue

                    defaults = {}

                    # --- Legacy Meta ---
                    defaults["legacy_nid"] = legacy_nid
                    defaults["legacy_vid"] = legacy_vid
                    defaults["legacy_status"] = parse_bool(row.get("status"))
                    defaults["legacy_created"] = parse_timestamp(row.get("created"))
                    defaults["legacy_changed"] = parse_timestamp(row.get("changed"))
                    # legacy_language: wir haben diese Info nicht direkt → leer lassen
                    defaults["legacy_language"] = ""
                    # Drupal-Spalte book_not_available (0/1) → Boolean-Feld not_available
                    # Drupal-Spalte book_not_available (0/1) → Boolean-Feld not_available
                    raw_not_avail = row.get("book_not_available")
                    if raw_not_avail is not None and str(raw_not_avail).strip() != "":
                        # explizit 0/1 o.ä. gesetzt → parse_bool
                        defaults["not_available"] = parse_bool(raw_not_avail)
                    # sonst: Feld gar nicht in defaults setzen → Django nimmt den Model-Default (False)

                    # --- Bundle & Name ---
                    defaults["bundle"] = row.get("type", "book") or "book"

                    # title → name
                    title_val = row.get("title", "").strip()
                    if title_val:
                        defaults["name"] = title_val

                    # --- einfache Felder mit gleichem Namen ---
                    for csv_col, value in row.items():
                        if csv_col in simple_fields:
                            field = simple_fields[csv_col]
                            cleaned = self._cast_value(field, value)
                            defaults[csv_col] = cleaned

                    # --- Felder mit anderem Namen (rename_map) ---
                    for csv_col, model_field_name in rename_map.items():
                        if csv_col not in row:
                            continue
                        value = row.get(csv_col, "")
                        field = Book._meta.get_field(model_field_name)
                        cleaned = self._cast_value(field, value)
                        defaults[model_field_name] = cleaned

                    # --- FK via *_tid ---
                    for csv_col, (model_cls, field_name) in fk_tid_fields.items():
                        tid_raw = row.get(csv_col)
                        tid = parse_int(tid_raw)
                        if tid is None:
                            defaults[field_name] = None
                            continue
                        try:
                            obj = model_cls.objects.get(legacy_tid=tid)
                            defaults[field_name] = obj
                        except model_cls.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"{model_cls.__name__} mit legacy_tid={tid} nicht gefunden "
                                    f"(Spalte {csv_col})"
                                )
                            )
                            defaults[field_name] = None

                    # Jetzt Book updaten/erstellen (ohne M2M)
                    book, created = Book.objects.update_or_create(
                        legacy_nid=legacy_nid,
                        defaults=defaults,
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                    # --- M2M via *_tid ---
                    # wir sammeln jeweils alle Objekte pro Feld und setzen sie komplett
                    for csv_col, (model_cls, field_name) in m2m_tid_fields.items():
                        tids = parse_tid_list(row.get(csv_col))
                        objs = []
                        for tid in tids:
                            try:
                                obj = model_cls.objects.get(legacy_tid=tid)
                                objs.append(obj)
                            except model_cls.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"{model_cls.__name__} (M2M) mit legacy_tid={tid} nicht gefunden "
                                        f"(Spalte {csv_col})"
                                    )
                                )
                        if objs:
                            getattr(book, field_name).set(objs)
                        else:
                            getattr(book, field_name).clear()

        self.stdout.write(
            self.style.SUCCESS(
                f"Buch-Import abgeschlossen. {created_count} erstellt, {updated_count} aktualisiert."
            )
        )

    # ---- Hilfsmethode zur Typkonvertierung ----
    def _cast_value(self, field, raw):
        if raw is None:
            return None
        val = str(raw)
        # leere Strings → None für Nicht-Char-Felder
        if isinstance(field, (dj_models.CharField, dj_models.TextField)):
            return val
        if val.strip() == "":
            return None

        if isinstance(field, dj_models.BooleanField):
            return parse_bool(val)
        if isinstance(field, dj_models.IntegerField):
            return parse_int(val)
        if isinstance(field, dj_models.FloatField):
            try:
                return float(val)
            except ValueError:
                return None
        if isinstance(field, dj_models.DateTimeField):
            # sollte hier nur selten vorkommen; sonst wie bei legacy_created
            return parse_timestamp(val)

        # default: String
        return val
