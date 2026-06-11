"""
Catalog-level data audit. Writes three CSVs into
``HASKALA_DUMPS_ROOT/<HASKALA_SLUG>/audit/`` and prints summary lines
so cron can chain it into an alert.

Four checks:

- orphan_places.csv — City rows that no Book / Person / Edition /
  Translation / Mention references. These leaked through the
  Drupal-6 importer when a side table didn't get re-linked.
- person_name_punctuation.csv — Person rows whose pref_label /
  german_name / hebrew_name starts with ``(``, ``)``, ``"``, ``'``
  or whitespace. Usually titles like ``(Dr.)`` that got into the
  name field instead of into a separate title column.
- duplicates.csv — Persons sharing the same pref_label or
  hebrew_name; same shape for Books and Cities.
- city_wikidata_status.csv — every live City with its current
  ``wikidata_id`` / ``parent_place`` / ``merged_into`` triple so
  the Phase 2 enrichment loop can find unanchored rows. Reports
  duplicate QIDs (two rows claiming the same anchor) as a
  separate warning line.

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

        wd_rows, wd_dupes = self._collect_city_wikidata_status()
        self._write_city_wikidata_status(
            out_dir / "city_wikidata_status.csv", wd_rows,
        )
        unanchored = sum(1 for r in wd_rows if not r["wikidata_id"])
        self.stdout.write(self.style.WARNING(
            f"city_wikidata_status: {len(wd_rows)} live cities, "
            f"{unanchored} without wikidata_id, "
            f"{len(wd_dupes)} duplicate QID group(s)"
        ))
        if wd_dupes:
            for qid, names in sorted(wd_dupes.items()):
                self.stdout.write(self.style.ERROR(
                    f"  duplicate QID {qid}: {', '.join(names)}"
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

    def _collect_city_wikidata_status(self):
        """Snapshot the Phase 1 anchor fields of every live City.

        Returns a tuple ``(rows, duplicates)`` where ``rows`` is a list
        of dicts (one per live city, alphabetical by name) and
        ``duplicates`` is ``{qid: [name, …]}`` for QIDs that show up
        on more than one row."""
        rows = []
        seen = {}
        for c in City.objects.filter(live=True).order_by("name"):
            qid = (c.wikidata_id or "").strip()
            parent = c.parent_place.name if c.parent_place_id else ""
            merged = c.merged_into.name if c.merged_into_id else ""
            rows.append({
                "uuid": str(c.pk),
                "name": c.name,
                "slug": c.slug or "",
                "wikidata_id": qid,
                "parent_place": parent,
                "merged_into": merged,
            })
            if qid:
                seen.setdefault(qid, []).append(c.name)
        duplicates = {q: names for q, names in seen.items() if len(names) > 1}
        return rows, duplicates

    def _write_city_wikidata_status(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "uuid", "name", "slug",
                    "wikidata_id", "parent_place", "merged_into",
                ],
            )
            w.writeheader()
            w.writerows(rows)
