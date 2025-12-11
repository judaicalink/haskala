import csv
import os

from django.core.management.base import BaseCommand, CommandError

from home.models import (
    City,
    Geolocation,
    Gender,
    Occupation,
    Topic,
    Language,
    Alignment,
    Font,
    Publisher,
    Series,
    TargetAudience,
    Typography,
    DateFormat,
    TextualModel,
    LanguageCount,
    FootnoteLocation,
    OriginalType,
    MentionDescription,
    ProductionRole,
)


class Command(BaseCommand):
    help = "Importiert Haskala-Taxonomien und Cities aus CSV-Dateien"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            type=str,
            help="Basisverzeichnis, in dem die Export-CSV-Dateien liegen",
            required=True,
        )

    # ---------- Hilfsfunktionen ----------

    def _open_csv(self, path):
        if not os.path.exists(path):
            raise CommandError(f"CSV-Datei nicht gefunden: {path}")
        self.stdout.write(self.style.NOTICE(f"Lese {path} ..."))
        return open(path, newline="", encoding="utf-8")

    def _import_simple_vocab(self, Model, csv_path, name_field="name"):
        """
        Importiert ein einfaches Vokabular:
        Erwartet Spalten: `tid`, `name` (oder konfigurierbar).
        """
        created_count = 0
        updated_count = 0

        with self._open_csv(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get("tid")
                if not tid:
                    continue
                try:
                    tid = int(tid)
                except ValueError:
                    continue

                name = row.get(name_field) or row.get("name") or ""
                name = name.strip()

                obj, created = Model.objects.update_or_create(
                    legacy_tid=tid,
                    defaults={"name": name},
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{Model.__name__}: {created_count} erstellt, {updated_count} aktualisiert."
            )
        )

    # ---------- Import-Methoden ----------

    def import_cities(self, base_dir):
        """
        Importiert Cities + Geolocation.
        Erwartete Spalten (aus deinem Notebook-Export):
        tid,vid,name,description,
        field_geolocation_lat,
        field_geolocation_lng,
        field_geolocation_lat_sin,
        field_geolocation_lat_cos,
        field_geolocation_lng_rad
        """
        path = os.path.join(base_dir, "cities_with_geolocation.csv")  # ggf. anpassen
        created_city = 0
        updated_city = 0
        created_geo = 0
        updated_geo = 0

        with self._open_csv(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get("tid")
                if not tid:
                    continue
                try:
                    tid_int = int(tid)
                except ValueError:
                    continue

                name = (row.get("name") or "").strip()

                # City anlegen / aktualisieren
                city, created = City.objects.update_or_create(
                    legacy_tid=tid_int,
                    defaults={
                        "name": name,
                        # optional: taxonomy vid etc.
                        # "legacy_vid": int(row.get("vid")) if row.get("vid") else None,
                    },
                )
                if created:
                    created_city += 1
                else:
                    updated_city += 1

                # Geolocation aus den Spalten lesen
                lat = row.get("field_geolocation_lat")
                lng = row.get("field_geolocation_lng")
                lat_sin = row.get("field_geolocation_lat_sin")
                lat_cos = row.get("field_geolocation_lat_cos")
                lng_rad = row.get("field_geolocation_lng_rad")

                # Wenn keine Koordinaten vorhanden sind, Geolocation überspringen
                if not any([lat, lng, lat_sin, lat_cos, lng_rad]):
                    continue

                def _to_float(value):
                    if value in (None, ""):
                        return None
                    try:
                        return float(value)
                    except ValueError:
                        return None

                defaults = {
                    "lat": _to_float(lat),
                    "lng": _to_float(lng),
                    "lat_sin": _to_float(lat_sin),
                    "lat_cos": _to_float(lat_cos),
                    "lng_rad": _to_float(lng_rad),
                }

                geo, created_geo_flag = Geolocation.objects.update_or_create(
                    city=city,
                    defaults=defaults,
                )
                if created_geo_flag:
                    created_geo += 1
                else:
                    updated_geo += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"City: {created_city} erstellt, {updated_city} aktualisiert."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Geolocation: {created_geo} erstellt, {updated_geo} aktualisiert."
            )
        )

    def handle(self, *args, **options):
        base_dir = options["base_dir"]

        if not os.path.isdir(base_dir):
            raise CommandError(f"{base_dir} ist kein Verzeichnis")

        # 1. Cities (Taxonomie vid=1 + Geolocation-Feld)
        self.import_cities(base_dir)

        # 2. Einfache Taxonomien
        # Passe die Dateinamen an deine tatsächlichen Export-Dateien an!
        vocab_files = [
            (Gender, "taxonomy_gender.csv"),
            (Occupation, "taxonomy_occupation.csv"),
            (Topic, "taxonomy_topics.csv"),
            (Alignment, "taxonomy_alignment.csv"),
            (Font, "taxonomy_fonts.csv"),
            (Publisher, "taxonomy_publishers.csv"),
            (Series, "taxonomy_series.csv"),
            (TargetAudience, "taxonomy_target_audience.csv"),
            (Typography, "taxonomy_typography.csv"),
            (DateFormat, "taxonomy_date_format.csv"),
            (TextualModel, "taxonomy_textual_models.csv"),
            (LanguageCount, "taxonomy_language_counts.csv"),
            (FootnoteLocation, "taxonomy_footnote_locations.csv"),
            (OriginalType, "taxonomy_original_type.csv"),
            (MentionDescription, "taxonomy_description_of_mentionee.csv"),
            (ProductionRole, "taxonomy_production_role.csv"),
        ]

        for Model, filename in vocab_files:
            csv_path = os.path.join(base_dir, filename)
            if not os.path.exists(csv_path):
                self.stdout.write(
                    self.style.WARNING(f"Überspringe {Model.__name__}: {filename} nicht gefunden.")
                )
                continue
            self._import_simple_vocab(Model, csv_path)

        # 3. Languages – wenn du sie als separates CSV exportiert hast
        # Z.B. Spalten: tid, name, language_code
        languages_path = os.path.join(base_dir, "taxonomy_languages.csv")
        if os.path.exists(languages_path):
            created = 0
            updated = 0
            with self._open_csv(languages_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tid = row.get("tid")
                    if not tid:
                        continue
                    try:
                        tid_int = int(tid)
                    except ValueError:
                        continue

                    name = (row.get("name") or "").strip()
                    code = (row.get("language_code") or "").strip()

                    obj, created_flag = Language.objects.update_or_create(
                        legacy_tid=tid_int,
                        defaults={
                            "name": name,
                            "language_code": code,
                        },
                    )
                    if created_flag:
                        created += 1
                    else:
                        updated += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Language: {created} erstellt, {updated} aktualisiert."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("Languages-CSV (taxonomy_languages.csv) nicht gefunden.")
            )

        self.stdout.write(self.style.SUCCESS("Taxonomie-Import abgeschlossen."))
