"""
Rewrite the Geolocation table from Wikidata so the public map only
shows pins anchored to Wikidata's authoritative coordinates.

For every live City with ``wikidata_id`` set, the command:

1. Fetches P625 (coordinate location) from the Wikidata entity.
2. Idempotently updates or creates the matching Geolocation row.

Cities without a ``wikidata_id`` are left as-is; the operator can
either set the QID first (then re-run) or remove the row entirely.

Default is dry-run — pass ``--apply`` to commit. Rate-limited
(default 0.6s between requests) and identifies itself in the
User-Agent per Wikidata's API etiquette.
"""
from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand

from home.models import City, Geolocation


USER_AGENT = (
    "haskala-catalog/1.0 "
    "(https://github.com/judaicalink/haskala; "
    "benjamin.schnabel@ephe.psl.eu) "
    "django-management-command"
)
ENTITY_URL = (
    "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
)


def _fetch_coord(session, qid):
    """Return ``(lat, lng)`` from the entity's P625 claim, or None
    if there is no coordinate statement on the item."""
    try:
        r = session.get(ENTITY_URL.format(qid=qid), timeout=15)
        r.raise_for_status()
        entity = r.json().get("entities", {}).get(qid)
    except (requests.RequestException, ValueError):
        return None
    if entity is None:
        return None
    for stmt in entity.get("claims", {}).get("P625", []):
        snak = stmt.get("mainsnak", {})
        dv = snak.get("datavalue", {})
        val = dv.get("value", {})
        lat = val.get("latitude")
        lng = val.get("longitude")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    return None


class Command(BaseCommand):
    help = (
        "Refresh the Geolocation table from Wikidata P625 for every "
        "live City whose wikidata_id is set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit the changes. Default: dry-run.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.6,
            help="Politeness delay between Wikidata requests. "
                 "Default 0.6s.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process at most N anchored cities. 0 = all.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        cities = (
            City.objects
            .filter(live=True)
            .exclude(wikidata_id="")
            .order_by("name")
        )
        if options["limit"]:
            cities = cities[: options["limit"]]
        cities = list(cities)

        self.stdout.write(
            f"Processing {len(cities)} anchored cities "
            f"(delay={options['delay']}s, apply={apply})"
        )

        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        updated = created = unchanged = no_p625 = 0
        for idx, c in enumerate(cities, 1):
            coord = _fetch_coord(session, c.wikidata_id)
            time.sleep(options["delay"])
            if coord is None:
                no_p625 += 1
                self.stdout.write(
                    f"  [{idx}/{len(cities)}] {c.name:30} "
                    f"-> {c.wikidata_id:10} no P625"
                )
                continue
            lat, lng = coord
            geo = Geolocation.objects.filter(city=c).first()
            if geo is None:
                self.stdout.write(
                    f"  [{idx}/{len(cities)}] {c.name:30} "
                    f"-> {c.wikidata_id:10} "
                    f"CREATE lat={lat:.4f} lng={lng:.4f}"
                )
                if apply:
                    Geolocation.objects.create(
                        city=c, lat=lat, lng=lng,
                    )
                created += 1
                continue
            same = (
                geo.lat is not None and geo.lng is not None
                and abs(geo.lat - lat) < 0.0005
                and abs(geo.lng - lng) < 0.0005
            )
            if same:
                unchanged += 1
                continue
            old = (geo.lat, geo.lng)
            self.stdout.write(
                f"  [{idx}/{len(cities)}] {c.name:30} "
                f"-> {c.wikidata_id:10} "
                f"UPDATE old={old} new=({lat:.4f}, {lng:.4f})"
            )
            if apply:
                geo.lat = lat
                geo.lng = lng
                geo.save(update_fields=["lat", "lng"])
            updated += 1

        self.stdout.write(self.style.WARNING(
            f"created:   {created}"
        ))
        self.stdout.write(self.style.WARNING(
            f"updated:   {updated}"
        ))
        self.stdout.write(self.style.WARNING(
            f"unchanged: {unchanged}"
        ))
        self.stdout.write(self.style.WARNING(
            f"no P625:   {no_p625}"
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                "DRY RUN: re-run with --apply to commit."
            ))
