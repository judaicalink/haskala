import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from home.models import Alignment


def parse_int(value):
    """
    Converts '402.0' -> 402, empty strings -> None.
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
    help = "Import Alignment taxonomy from taxonomy_alignment.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the CSV file (e.g. research/export/taxonomy_alignment.csv)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])
        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        self.stdout.write(f"Reading Alignment CSV: {csv_path}")

        created_count = 0
        updated_count = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_tid = row.get("tid")
                name = (row.get("name") or "").strip()

                if not name:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping row without name (tid={raw_tid!r})"
                        )
                    )
                    continue

                legacy_tid = parse_int(raw_tid)

                lookup = {}
                if legacy_tid is not None:
                    lookup["legacy_tid"] = legacy_tid
                else:
                    lookup["name"] = name

                obj, created = Alignment.objects.update_or_create(
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
                f"Alignment import finished. "
                f"{created_count} created, {updated_count} updated."
            )
        )
