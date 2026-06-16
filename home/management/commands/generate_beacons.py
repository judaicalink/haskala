"""
Generate BEACON link-dump files from the Haskala catalog so library
discovery tools (GND, VIAF, Wikidata) and Judaicalink-style
aggregators can advertise the back-links from their authority
records into our catalog. Beacon is a one-line-per-link plain text
format -- spec at https://gbv.github.io/beaconspec/beacon.html.

Per BEACON file we emit:

  #FORMAT: BEACON
  #PREFIX: https://<authority>/{id}
  #TARGET: https://www.haskala-library.net/<entity>/{ID}/
  #NAME: Haskala-Bibliothek
  #INSTITUTION: École Pratique des Hautes Études
  #DESCRIPTION: …
  #CONTACT: benjamin.schnabel@ephe.psl.eu
  #TIMESTAMP: 2026-06-16T12:00:00Z
  #FEED: …

  <authority-id>|<haskala-slug>

The pipe-separated ``id|slug`` line means "the authority record
<authority>/{id} is described locally at <TARGET>/{slug}/".

Six output files (one per (entity, authority) combination):

  beacon-gnd-persons.txt           Person.gnd_id          -> /persons/
  beacon-viaf-persons.txt          Person.viaf_id         -> /persons/
  beacon-wikidata-persons.txt      Person.wikidata_id     -> /persons/
  beacon-wikidata-places.txt       City.wikidata_id       -> /places/
  beacon-wikidata-topics.txt       Topic.wikidata_id      -> /topics/

(Topics don't have a wikidata_id field yet -- the loop guards on
``hasattr``, so it picks up the file automatically once the field
exists.)

Output goes to ``<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/beacon/``.

Run via cron once a month (see
docs/operations/beacon-generator.md).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from home.models import City, Person, Topic


BASE_URL = (
    getattr(settings, "HASKALA_BASE_URL", "")
    or getattr(settings, "WAGTAILADMIN_BASE_URL", "")
    or "https://www.haskala-library.net"
).rstrip("/")

INSTITUTION = "École Pratique des Hautes Études"
CONTACT = "benjamin.schnabel@ephe.psl.eu"


# (entity_label, model, attr, route, prefix_url, description)
BEACON_JOBS = [
    (
        "gnd-persons", Person, "gnd_id", "persons",
        "https://d-nb.info/gnd/",
        "GND (Gemeinsame Normdatei) identifiers of persons in the "
        "Haskala-Bibliothek catalog.",
    ),
    (
        "viaf-persons", Person, "viaf_id", "persons",
        "https://viaf.org/viaf/",
        "VIAF (Virtual International Authority File) identifiers "
        "of persons in the Haskala-Bibliothek catalog.",
    ),
    (
        "wikidata-persons", Person, "wikidata_id", "persons",
        "https://www.wikidata.org/wiki/",
        "Wikidata QIDs of persons in the Haskala-Bibliothek "
        "catalog.",
    ),
    (
        "wikidata-places", City, "wikidata_id", "places",
        "https://www.wikidata.org/wiki/",
        "Wikidata QIDs of places in the Haskala-Bibliothek catalog.",
    ),
    (
        "wikidata-topics", Topic, "wikidata_id", "topics",
        "https://www.wikidata.org/wiki/",
        "Wikidata QIDs of topics in the Haskala-Bibliothek catalog.",
    ),
]


class Command(BaseCommand):
    help = (
        "Emit BEACON link-dump files mapping GND / VIAF / Wikidata "
        "authority records to the matching Haskala catalog pages."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out-dir",
            default=None,
            help="Output directory. Default: "
                 "<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/beacon/",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"] or (
            Path(settings.HASKALA_DUMPS_ROOT) / settings.HASKALA_SLUG
            / "beacon"
        ))
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        for (
            label, model, attr, route, prefix_url, description,
        ) in BEACON_JOBS:
            if not hasattr(model, attr):
                self.stdout.write(self.style.WARNING(
                    f"  skip {label}: {model.__name__}.{attr} "
                    f"field not present"
                ))
                continue

            out_path = out_dir / f"beacon-{label}.txt"
            count = self._write_beacon(
                out_path, model, attr, route, prefix_url,
                description, timestamp,
            )
            self.stdout.write(self.style.WARNING(
                f"  {label:25} {count:4} links -> {out_path.name}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"BEACON files written to {out_dir}"
        ))

    def _write_beacon(
        self,
        out_path,
        model,
        attr,
        route,
        prefix_url,
        description,
        timestamp,
    ):
        qs = (
            model.objects
            .filter(**{f"{attr}__gt": ""})
            .exclude(**{attr: ""})
            .order_by(attr)
        )
        # Restrict Person rows to actual humans -- organizations
        # use different authority-record families and shouldn't be
        # advertised against, say, GND-Tp.
        if model is Person and hasattr(model, "entity_type"):
            qs = qs.filter(entity_type="person")
        # Restrict City rows to live + non-merged ones so merged
        # alternate rows (Pressburg -> Bratislava) don't show up
        # alongside their canonical.
        if model is City:
            qs = qs.filter(live=True, merged_into__isnull=True)

        target_url = f"{BASE_URL}/{route}/{{ID}}/"
        feed_slug = out_path.stem.split("-", 1)[1]
        feed_url = f"{BASE_URL}/data/beacon-{feed_slug}.txt"

        with out_path.open("w", encoding="utf-8") as f:
            f.write("#FORMAT: BEACON\n")
            f.write(f"#PREFIX: {prefix_url}\n")
            f.write(f"#TARGET: {target_url}\n")
            f.write("#NAME: Haskala-Bibliothek\n")
            f.write(f"#INSTITUTION: {INSTITUTION}\n")
            f.write(f"#DESCRIPTION: {description}\n")
            f.write(f"#CONTACT: {CONTACT}\n")
            f.write(f"#TIMESTAMP: {timestamp}\n")
            f.write(f"#FEED: {feed_url}\n")
            f.write("\n")

            count = 0
            for row in qs:
                aid = (getattr(row, attr) or "").strip()
                slug = (row.slug or "").strip()
                if not aid or not slug:
                    continue
                f.write(f"{aid}|{slug}\n")
                count += 1

        return count
