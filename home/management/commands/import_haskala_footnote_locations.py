import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from home.models import FootnoteLocation


def parse_int(value):
    """
    Helper, analog zu den anderen Importern:
    - behandelt '402.0' etc. korrekt
    - gibt None zurück, wenn leer oder ungültig
    """
    if value is None:
        return None
    val = str(value).strip()
    if val == "":
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Importiert FootnoteLocation-Einträge aus einer CSV (location_of_footnotes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Pfad zur CSV-Datei (z. B. research/export/location_of_footnotes.csv)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])
        if not csv_path.exists():
            raise CommandError(f"Datei nicht gefunden: {csv_path}")

        self.stdout.write(f"Lese FootnoteLocation-CSV: {csv_path}")

        created_count = 0
        updated_count = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Versuche, die relevanten Spalten zu lesen
                # Passe diese ggf. an deine CSV an:
                # - 'tid'   -> Drupal TID
                # - 'name'  -> Klartext-Bezeichnung
                raw_tid = row.get("tid")
                name = (row.get("name") or "").strip()

                # Wenn name leer ist, überspringen wir den Datensatz
                if not name:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Überspringe Zeile ohne Name (tid={raw_tid!r})"
                        )
                    )
                    continue

                legacy_tid = parse_int(raw_tid)

                # Wir versuchen, primär nach legacy_tid zu matchen, wenn vorhanden.
                # Fallback: nach name.
                lookup = {}
                if legacy_tid is not None:
                    lookup["legacy_tid"] = legacy_tid
                else:
                    # Kein TID -> wir matchen über den Namen
                    lookup["name"] = name

                obj, created = FootnoteLocation.objects.update_or_create(
                    **lookup,
                    defaults={
                        "name": name,
                        "legacy_tid": legacy_tid,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"FootnoteLocation-Import abgeschlossen. "
                f"{created_count} erstellt, {updated_count} aktualisiert."
            )
        )
