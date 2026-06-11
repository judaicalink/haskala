"""
Surface City rows that need a manual sanity check against Wikidata.

Three classifiers, written into a single CSV worklist:

1. **Outside Europe/Israel** — has Geolocation but the (lat, lng) falls
   outside a generous Europe + Levant bounding box (lat 29-72,
   lng -10 to 60). The Drupal-6 importer geocoded by name alone, so
   "Buda" landed on a Texas hamlet and "Kolmar" on a New Zealand
   farm; these are the rows that need their wikidata_id paste fixed
   first.

2. **Missing coordinates** — live City with no Geolocation row at all.
   Curators can't render it on the map and the geo bias used by
   Phase 2 has nothing to work with.

3. **Suspicious name** — the name itself looks wrong: contains a
   digit, an at-sign or other URL-shaped character, an obvious
   personname comma ("Surname, Firstname"), is shorter than 3
   characters, or longer than 40 (multi-place strings).

Each row carries the reason string ("outside_eu_il" /
"missing_coords" / "suspicious_name") plus, where relevant, the
offending coordinate and a hint at the likely-correct continent
(e.g. "North America" / "Africa" / "Oceania") so the curator can
spot the geocoding direction at a glance.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from home.models import City, Geolocation


# Generous Europe + Levant box. Includes UK, Scandinavia, all the
# Russian-Polish-Lithuanian corridor, the Caucasus, North Africa, the
# Levant, and the southern tip of Iberia. Anything outside is worth a
# manual check.
EU_LEVANT_BOX = {
    "lat_min": 29.0,
    "lat_max": 72.0,
    "lng_min": -10.0,
    "lng_max": 60.0,
}

SUSPICIOUS_NAME_RE = re.compile(
    # any of: digit, at-sign, percent, ampersand, less-than,
    # equals, slash, backslash, pipe, semicolon
    r"[\d@%&<=/\\|;]"
)

# "Surname, Firstname" looks like a person mistakenly stored as a
# place — the comma plus a space plus a capital letter is the tell.
PERSON_NAME_RE = re.compile(r",\s+[A-ZÀ-Ÿ]")


def continent_hint(lat, lng):
    """One-word region label so the worklist row tells the curator
    where the bad coordinate actually points. Coarse on purpose."""
    if lat < 0:
        if lng < 50:
            return "South Africa or Oceania"
        return "Oceania"
    if -170 <= lng <= -30:
        return "North America"
    if 60 < lng <= 145:
        return "Asia"
    if -30 < lng < -10 and lat < 30:
        return "Africa"
    return "outside box"


class Command(BaseCommand):
    help = (
        "Write a CSV of live cities that need a manual Wikidata "
        "check: bad coordinates, missing coordinates, suspicious "
        "names."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="docs/audits/places_for_review.csv",
            help="Output path. Default: "
                 "docs/audits/places_for_review.csv.",
        )

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        geos = {
            g.city_id: (g.lat, g.lng)
            for g in Geolocation.objects.filter(
                lat__isnull=False, lng__isnull=False,
            )
        }

        rows = []
        outside, missing, suspicious = 0, 0, 0
        for c in City.objects.filter(live=True).order_by("name"):
            base = {
                "uuid": str(c.pk),
                "name": c.name,
                "slug": c.slug or "",
                "wikidata_id": c.wikidata_id or "",
            }
            coord = geos.get(c.pk)

            # 1. Outside Europe/Israel
            if coord is not None:
                lat, lng = coord
                if not (
                    EU_LEVANT_BOX["lat_min"] <= lat
                    <= EU_LEVANT_BOX["lat_max"]
                    and EU_LEVANT_BOX["lng_min"] <= lng
                    <= EU_LEVANT_BOX["lng_max"]
                ):
                    outside += 1
                    rows.append({
                        **base,
                        "reason": "outside_eu_il",
                        "lat": f"{lat:.4f}",
                        "lng": f"{lng:.4f}",
                        "hint": continent_hint(lat, lng),
                    })
                    continue
            else:
                # 2. Missing coordinates
                missing += 1
                rows.append({
                    **base,
                    "reason": "missing_coords",
                    "lat": "",
                    "lng": "",
                    "hint": "",
                })
                # don't `continue` — still let the name be checked
                # for suspiciousness below

            # 3. Suspicious-looking name
            name = c.name or ""
            reasons = []
            if SUSPICIOUS_NAME_RE.search(name):
                reasons.append("digit_or_symbol")
            if PERSON_NAME_RE.search(name):
                reasons.append("person_name_pattern")
            if len(name.strip()) < 3:
                reasons.append("too_short")
            if len(name.strip()) > 40:
                reasons.append("too_long")
            if reasons:
                suspicious += 1
                rows.append({
                    **base,
                    "reason": "suspicious_name:" + ",".join(reasons),
                    "lat": f"{coord[0]:.4f}" if coord else "",
                    "lng": f"{coord[1]:.4f}" if coord else "",
                    "hint": "",
                })

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "uuid", "name", "slug",
                    "wikidata_id", "reason", "lat", "lng", "hint",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.WARNING(
            f"outside_eu_il:    {outside}"
        ))
        self.stdout.write(self.style.WARNING(
            f"missing_coords:   {missing}"
        ))
        self.stdout.write(self.style.WARNING(
            f"suspicious_name:  {suspicious}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} row(s) total -> {out_path}"
        ))
