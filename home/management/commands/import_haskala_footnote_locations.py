import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from home.models import FootnoteLocation


def parse_int(value):
    """
    Helper, analogous to the other importers:
    - handles '402.0' etc. correctly
    - returns None if empty or invalid
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
    help = "Import FootnoteLocation entries from a CSV (location_of_footnotes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the CSV file (e.g. research/export/location_of_footnotes.csv)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])
        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        self.stdout.write(f"Reading FootnoteLocation CSV: {csv_path}")

        created_count = 0
        updated_count = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try to read the relevant columns
                # Adjust these to your CSV if necessary:
                # - 'tid'   -> Drupal TID
                # - 'name'  -> plain-text label
                raw_tid = row.get("tid")
                name = (row.get("name") or "").strip()

                # If name is empty, skip the record
                if not name:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping row without name (tid={raw_tid!r})"
                        )
                    )
                    continue

                legacy_tid = parse_int(raw_tid)

                # Match primarily by legacy_tid if present.
                # Fallback: match by name.
                lookup = {}
                if legacy_tid is not None:
                    lookup["legacy_tid"] = legacy_tid
                else:
                    # No TID -> match by name
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
                f"FootnoteLocation import finished. "
                f"{created_count} created, {updated_count} updated."
            )
        )
