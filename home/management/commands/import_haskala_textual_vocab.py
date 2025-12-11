import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from home.models import TextualModel, Alignment


def _parse_int_or_none(value):
    """
    Nimmt Werte wie '341', '341.0' oder '' und macht daraus int bzw. None.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        # Einige Exporte haben '341.0'
        return int(float(value))
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Importiert Textual Models und Alignment-Taxonomien aus CSV-Dateien."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            default="research/export",
            help="Verzeichnis mit taxonomy_textual_models.csv und taxonomy_alignment.csv",
        )

    def handle(self, *args, **options):
        base_dir = Path(options["base_dir"])

        self.import_textual_models(base_dir / "taxonomy_textual_models.csv")
        self.import_alignment(base_dir / "taxonomy_alignment.csv")

    # -------- Textual Models --------

    def import_textual_models(self, path: Path):
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(f"Überspringe TextualModel: {path} nicht gefunden.")
            )
            return

        created = 0
        updated = 0

        self.stdout.write(f"Lese Textual Models aus {path} ...")
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_tid = _parse_int_or_none(row.get("tid"))
                name = (row.get("name") or "").strip()

                if legacy_tid is None or not name:
                    # kaputte/leer Zeile überspringen
                    continue

                obj, is_created = TextualModel.objects.update_or_create(
                    legacy_tid=legacy_tid,
                    defaults={"name": name},
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"TextualModel: {created} erstellt, {updated} aktualisiert."
            )
        )

    # -------- Alignment --------

    def import_alignment(self, path: Path):
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(f"Überspringe Alignment: {path} nicht gefunden.")
            )
            return

        created = 0
        updated = 0

        self.stdout.write(f"Lese Alignment aus {path} ...")
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                legacy_tid = _parse_int_or_none(row.get("tid"))
                name = (row.get("name") or "").strip()

                if legacy_tid is None or not name:
                    continue

                obj, is_created = Alignment.objects.update_or_create(
                    legacy_tid=legacy_tid,
                    defaults={"name": name},
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Alignment: {created} erstellt, {updated} aktualisiert."
            )
        )
