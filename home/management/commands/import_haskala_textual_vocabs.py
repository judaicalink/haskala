import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from home.models import Alignment, OriginalType, TextualModel


def parse_int(value, default=None):
    """
    Hilfsfunktion: wandelt Strings wie '', 'nan' etc. robust in int oder default.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


class Command(BaseCommand):
    help = "Importiert Alignment, OriginalType und TextualModel aus den Taxonomie-Exports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            required=True,
            help="Basisverzeichnis der Export-CSV-Dateien (z. B. research/export)",
        )

    # ---------- Hilfsfunktion für einfache Vokabulare ----------

    def import_simple_vocab(self, path: Path, model, label: str):
        """
        Erwartetes CSV-Schema: tid, vid, name, description
        -> model muss Felder name und legacy_tid haben.
        """
        if not path.exists():
            self.stdout.write(f"Überspringe {label}: {path.name} nicht gefunden.")
            return

        created = 0
        updated = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = parse_int(row.get("tid"))
                name = (row.get("name") or "").strip()

                if tid is None or not name:
                    # Leere oder kaputte Zeilen überspringen
                    continue

                obj, is_created = model.objects.update_or_create(
                    legacy_tid=tid,
                    defaults={
                        "name": name,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            f"{label}: {created} erstellt, {updated} aktualisiert."
        )

    # ---------- Handle ----------

    def handle(self, *args, **options):
        base_dir = Path(options["base_dir"]).expanduser().resolve()
        if not base_dir.exists():
            raise CommandError(f"Basisverzeichnis existiert nicht: {base_dir}")

        self.stdout.write(f"Nutze Basisverzeichnis: {base_dir}")

        # Alignment (taxonomy_alignment.csv)
        alignment_csv = base_dir / "taxonomy_alignment.csv"
        self.import_simple_vocab(alignment_csv, Alignment, "Alignment")

        # OriginalType (taxonomy_original_type.csv)
        original_type_csv = base_dir / "taxonomy_original_type.csv"
        self.import_simple_vocab(original_type_csv, OriginalType, "OriginalType")

        # TextualModel (taxonomy_textual_models.csv)
        textual_models_csv = base_dir / "taxonomy_textual_models.csv"
        self.import_simple_vocab(textual_models_csv, TextualModel, "TextualModel")

        self.stdout.write(self.style.SUCCESS("Import der Text-Vokabulare abgeschlossen."))
