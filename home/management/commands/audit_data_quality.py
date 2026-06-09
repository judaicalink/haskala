"""
Catalog-level data audit. Writes three CSVs into
``HASKALA_DUMPS_ROOT/<HASKALA_SLUG>/audit/`` and prints summary lines
so cron can chain it into an alert.

Three checks:

- orphan_places.csv — City rows that no Book / Person / Edition /
  Translation / Mention references. These leaked through the
  Drupal-6 importer when a side table didn't get re-linked.
- person_name_punctuation.csv — Person rows whose pref_label /
  german_name / hebrew_name starts with ``(``, ``)``, ``"``, ``'``
  or whitespace. Usually titles like ``(Dr.)`` that got into the
  name field instead of into a separate title column.
- duplicates.csv — Persons sharing the same pref_label or
  hebrew_name; same shape for Books and Cities.

The command is read-only. Use the dedicated fix commands
(``clean_person_names``, ``mark_orphan_places_draft``) to act on
the report.
"""
from __future__ import annotations

import csv
from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import (
    Book, City, Edition, Mention, Person, Translation,
)


LEADING_PUNCT_RE = re.compile(r'^[(")\'\s,.;:]')


class Command(BaseCommand):
    help = "Audit the catalog for orphan places, name punctuation noise, duplicates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out-dir",
            default=None,
            help="Directory to write CSV reports into. Default: "
                 "<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/audit/",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"] or (
            Path(settings.HASKALA_DUMPS_ROOT) / settings.HASKALA_SLUG / "audit"
        ))
        out_dir.mkdir(parents=True, exist_ok=True)

        orphans = self._collect_orphan_places()
        self._write_orphan_places(out_dir / "orphan_places.csv", orphans)
        self.stdout.write(self.style.WARNING(
            f"orphan_places: {len(orphans)} / {City.objects.count()}"
        ))

        punct = self._collect_name_punctuation()
        self._write_name_punctuation(out_dir / "person_name_punctuation.csv", punct)
        self.stdout.write(self.style.WARNING(
            f"person_name_punctuation: {len(punct)} field/value pairs"
        ))

        dups = self._collect_duplicates()
        self._write_duplicates(out_dir / "duplicates.csv", dups)
        self.stdout.write(self.style.WARNING(
            f"duplicates: {sum(len(v) for v in dups.values())} keys "
            f"across {sum(len(rows) for v in dups.values() for rows in v.values())} rows"
        ))

        self.stdout.write(self.style.SUCCESS(f"Reports written to {out_dir}"))

    # ----- collectors ---------------------------------------------

    def _collect_orphan_places(self):
        orphans = []
        for c in City.objects.all():
            if Book.objects.filter(
                Q(publication_place=c)
                | Q(publication_place_other=c)
                | Q(original_publication_place=c)
            ).exists():
                continue
            if Person.objects.filter(
                Q(place_of_birth=c) | Q(place_of_death=c)
            ).exists():
                continue
            if Edition.objects.filter(city=c).exists():
                continue
            if Translation.objects.filter(city=c).exists():
                continue
            if Mention.objects.filter(mentionee_city=c).exists():
                continue
            orphans.append(c)
        return orphans

    def _collect_name_punctuation(self):
        out = []
        for p in Person.objects.all():
            for fname in ("pref_label", "german_name", "hebrew_name"):
                value = (getattr(p, fname, "") or "").strip()
                if value and LEADING_PUNCT_RE.match(value):
                    out.append((p, fname, value))
        return out

    def _collect_duplicates(self):
        """Returns {model_name: {key: [pks…]}} for keys with len>1."""
        result = {}
        for model, fields in [
            (Person, ("pref_label", "german_name", "hebrew_name")),
            (Book, ("name",)),
            (City, ("name",)),
        ]:
            per_model = {}
            for fname in fields:
                groups = {}
                for o in model.objects.all():
                    key = (getattr(o, fname, "") or "").strip().lower()
                    if not key:
                        continue
                    groups.setdefault((fname, key), []).append(o.pk)
                for k, ids in groups.items():
                    if len(ids) > 1:
                        per_model[k] = ids
            result[model.__name__] = per_model
        return result

    # ----- writers ------------------------------------------------

    def _write_orphan_places(self, path, orphans):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["uuid", "name", "slug", "live"])
            for c in orphans:
                w.writerow([c.pk, c.name, c.slug, c.live])

    def _write_name_punctuation(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["uuid", "field", "current_value"])
            for p, fname, value in rows:
                w.writerow([p.pk, fname, value])

    def _write_duplicates(self, path, dups):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["model", "field", "value", "uuids"])
            for model_name, by_key in dups.items():
                for (fname, key), ids in sorted(by_key.items()):
                    w.writerow([model_name, fname, key, ";".join(str(i) for i in ids)])
