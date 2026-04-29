import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from home.models import Alignment, OriginalType, TextualModel


def parse_int(value, default=None):
    """
    Helper: robustly converts strings like '', 'nan' etc. to int or default.
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
    help = "Import Alignment, OriginalType and TextualModel from the taxonomy exports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            required=True,
            help="Base directory of the export CSV files (e.g. research/export)",
        )

    # ---------- Helper for simple vocabularies ----------

    def import_simple_vocab(self, path: Path, model, label: str):
        """
        Expected CSV schema: tid, vid, name, description
        -> model must have fields name and legacy_tid.
        """
        if not path.exists():
            self.stdout.write(f"Skipping {label}: {path.name} not found.")
            return

        created = 0
        updated = 0

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = parse_int(row.get("tid"))
                name = (row.get("name") or "").strip()

                if tid is None or not name:
                    # Skip empty or broken rows
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
            f"{label}: {created} created, {updated} updated."
        )

    # ---------- Handle ----------

    def handle(self, *args, **options):
        base_dir = Path(options["base_dir"]).expanduser().resolve()
        if not base_dir.exists():
            raise CommandError(f"Base directory does not exist: {base_dir}")

        self.stdout.write(f"Using base directory: {base_dir}")

        # Alignment (taxonomy_alignment.csv)
        alignment_csv = base_dir / "taxonomy_alignment.csv"
        self.import_simple_vocab(alignment_csv, Alignment, "Alignment")

        # OriginalType (taxonomy_original_type.csv)
        original_type_csv = base_dir / "taxonomy_original_type.csv"
        self.import_simple_vocab(original_type_csv, OriginalType, "OriginalType")

        # TextualModel (taxonomy_textual_models.csv)
        textual_models_csv = base_dir / "taxonomy_textual_models.csv"
        self.import_simple_vocab(textual_models_csv, TextualModel, "TextualModel")

        self.stdout.write(self.style.SUCCESS("Text vocabularies import finished."))
